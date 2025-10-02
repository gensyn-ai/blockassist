import dotenv

dotenv.load_dotenv()


import asyncio
import logging
import os
import sys
from enum import Enum
from pathlib import Path

import hydra
from huggingface_hub import login, whoami
from omegaconf import DictConfig

from blockassist import telemetry
from blockassist.blockchain.coordinator import ModalSwarmCoordinator
from blockassist.data import (
    backup_evaluate_dirs,
    delete_evaluate_dirs,
    delete_evaluate_zips,
    get_total_episodes,
    restore_evaluate_dirs_from_backup,
    zip_and_upload_all_episodes,
    zip_and_upload_episodes,
)
from blockassist.distributed.hf import upload_to_huggingface
from blockassist.episode import EpisodeRunner
from blockassist.globals import (
    _DEFAULT_CHECKPOINT,
    _DEFAULT_EPISODES_S3_BUCKET,
    get_logger,
    get_training_id,
)
from blockassist.train import TrainingRunner

_LOG = get_logger()


class Stage(Enum):
    BACKUP_EVALUATE = "backup_evaluate"
    CLEAN_EVALUATE = "clean_evaluate"
    RESTORE_BACKUP = "restore_backup"
    EPISODE = "episode"
    UPLOAD_EPISODES = "upload_episodes"
    TRAIN = "train"
    UPLOAD_MODEL = "upload_model"


_ALL_STAGES = [
    Stage.BACKUP_EVALUATE,
    Stage.CLEAN_EVALUATE,
    Stage.EPISODE,
    Stage.UPLOAD_EPISODES,
    Stage.TRAIN,
    Stage.UPLOAD_MODEL,
]


def get_stages(cfg: DictConfig) -> list[Stage]:
    # Overrides mode
    if "stages" in cfg and cfg["stages"]:
        return [Stage(stage) for stage in cfg["stages"]]

    mode = cfg["mode"]
    if mode == "e2e":
        return _ALL_STAGES

    return []


def hf_login(cfg: DictConfig):
    hf_token = cfg.get("hf_token")
    login(hf_token)
    return hf_token


def get_hf_repo_id(hf_token: str, training_id: str):
    username = whoami(token=hf_token)["name"]
    return f"{username}/blockassist"


async def _main(cfg: DictConfig):
    try:
        logging.basicConfig(
            filename="logs/blockassist.log", encoding="utf-8", level=logging.DEBUG
        )
        if cfg["mode"] == "e2e":
            _LOG.info("Starting full recording session!!")

        # Chain configuration
        org_id = cfg.get("org_id")
        address_eoa = cfg.get("address_eoa")
        if not org_id or not address_eoa:
            raise ValueError("Missing org_id or address_eoa in configuration.")

        coordinator = ModalSwarmCoordinator(org_id)
        training_id = get_training_id(address_eoa)

        # Check that HF token exists and is non-empty.
        if not cfg["hf_token"]:
            raise ValueError("Missing hf_token in configuration.")

        # Training configuration
        num_instances = cfg.get("num_instances", 2)
        checkpoint_dir = cfg.get("checkpoint_dir", _DEFAULT_CHECKPOINT)
        model_dir = cfg.get("model_dir", "")
        num_training_iters = cfg.get("num_training_iters", 0)
        upload_session_episodes_only = cfg.get("upload_session_episodes_only", True)

        stages = get_stages(cfg)
        for stage in stages:
            if stage == Stage.BACKUP_EVALUATE:
                _LOG.info("Backing up existing evaluation directories!!")
                backup_evaluate_dirs(checkpoint_dir)

            elif stage == Stage.CLEAN_EVALUATE:
                _LOG.info("Cleaning up evaluation directories and zip files!!")
                delete_evaluate_dirs(checkpoint_dir)
                delete_evaluate_zips(checkpoint_dir)

            elif stage == Stage.RESTORE_BACKUP:
                _LOG.info("Restoring backup evaluation directories!!")
                restore_evaluate_dirs_from_backup(checkpoint_dir)

            elif stage == Stage.EPISODE:
                _LOG.info("Starting episode recording!!")
                episode_runner = EpisodeRunner(
                    address_eoa,
                    checkpoint_dir,
                    human_alone=num_instances == 1,
                )
                episode_runner.start()
                await episode_runner.wait_for_end()

            elif stage == Stage.UPLOAD_EPISODES:
                if upload_session_episodes_only:
                    _LOG.info("Uploading session episode zips!")
                    s3_uris = zip_and_upload_episodes(
                        address_eoa,
                        checkpoint_dir,
                        _DEFAULT_EPISODES_S3_BUCKET,
                        episode_runner.evaluate_dirs,
                    )
                else:
                    _LOG.info("Uploading all episode zips!")
                    s3_uris = zip_and_upload_all_episodes(
                        address_eoa,
                        checkpoint_dir,
                        _DEFAULT_EPISODES_S3_BUCKET,
                    )
                _LOG.info(
                    f"Episode data uploaded successfully! Uploaded {len(s3_uris)} files."
                )

            elif stage == Stage.TRAIN:
                _LOG.info("Starting model training!!")
                training_runner = TrainingRunner(address_eoa, num_training_iters)
                training_runner.start()
                model_dir = training_runner.model_dir
                await training_runner.wait_for_end()

            elif stage == Stage.UPLOAD_MODEL:
                _LOG.info("Starting model upload!!")
                if model_dir:
                    hf_token = hf_login(cfg)
                    hf_repo_id = get_hf_repo_id(hf_token, training_id)
                    num_sessions = get_total_episodes(checkpoint_dir)
                    is_telemetry_enabled = not telemetry.is_telemetry_disabled()
                    git_ref = upload_to_huggingface(
                        model_path=Path(model_dir),
                        user_id=address_eoa,
                        repo_id=hf_repo_id,
                        address_eoa=address_eoa,
                        hf_token=hf_token,
                        chain_metadata_dict={
                            "eoa": cfg.get("address_account"),
                            "trainingId": training_id,
                            "numSessions": num_sessions,
                            "telemetryEnabled": is_telemetry_enabled,
                        },
                    )
                    coordinator.submit_hf_upload(
                        training_id=training_id,
                        hf_id=hf_repo_id,
                        num_sessions=num_sessions,
                        telemetry_enabled=is_telemetry_enabled,
                        git_ref=git_ref,
                    )
                else:
                    _LOG.warning("No model directory specified, skipping upload.")
                    continue

    except Exception as e:
        _LOG.error("Recording session was stopped with exception", exc_info=e)
        sys.exit(1)


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(cfg: DictConfig) -> None:
    asyncio.run(_main(cfg))


if __name__ == "__main__":
    os.environ["HYDRA_FULL_ERROR"] = "1"
    main()
