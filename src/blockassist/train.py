import asyncio
import os
import shutil
import time
from pathlib import Path

from mbag.environment.goals import ALL_GOAL_GENERATORS
from mbag.scripts.convert_human_data_to_rllib import ex as convert_ex
from mbag.scripts.train import ex as train_ex
from sacred.observers import FileStorageObserver

from blockassist import telemetry
from blockassist.data import get_total_episodes
from blockassist.globals import (
    _DEFAULT_CHECKPOINT,
    get_logger,
)
from blockassist.goals.generator import BlockAssistGoalGenerator

_LOG = get_logger()

convert_ex.observers.append(FileStorageObserver.create("convert_runs"))
train_ex.observers.append(FileStorageObserver.create("train_runs"))


def run_train_main(mbag_config: dict, rllib_path: str, num_training_iters: int):
    ALL_GOAL_GENERATORS["blockassist"] = BlockAssistGoalGenerator
    result = train_ex.run(
        named_configs=["bc_human"],
        config_updates={
            "data_split": "human_with_assistant",
            "goal_generator": "blockassist",
            "input": rllib_path,
            "num_training_iters": num_training_iters,
        },
    ).result
    assert result
    return result


@convert_ex.named_config
def blockassist_convert():
    max_seq_len = 32  # noqa: F841
    inventory_player_indices = [0, 1]  # noqa: F841

    data_dir = _DEFAULT_CHECKPOINT
    data_glob = os.path.join(data_dir, "evaluate_*", "**", "episodes.zip")  # noqa: F841
    out_dir = os.path.join(data_dir, "..", "rllib")  # noqa: F841


def run_convert_main():
    result = convert_ex.run(named_configs=["blockassist_convert"]).result
    assert result
    return result


class TrainingRunner:
    """Class for managing a Minecraft bot training session."""

    def __init__(
        self,
        address_eoa: str,
        num_training_iters: int = 1,
        checkpoint_dir=_DEFAULT_CHECKPOINT,
    ):
        self.address_eoa = address_eoa

        self.num_training_iters = num_training_iters
        self.checkpoint_dir = checkpoint_dir
        self.model_dir = None

        self.training_started = asyncio.Event()
        self.training_ended = asyncio.Event()

        self.start_time = time.time()
        self.end_time = None

    def wait_for_start(self, timeout=60 * 2):  # minutes
        return asyncio.wait_for(self.training_started.wait(), timeout)

    def wait_for_end(self, timeout=60 * 60 * 24):  # hours
        return asyncio.wait_for(self.training_ended.wait(), timeout)

    def before_training(self):
        _LOG.info("Training started.")
        self.training_started.set()

        _LOG.info("Conversion started!")
        rllib_path = Path(self.checkpoint_dir) / ".." / "rllib"
        shutil.rmtree(rllib_path, ignore_errors=True)
        self.convert_result = run_convert_main()

    def after_training(self):
        _LOG.info("Training ended.")
        self.end_time = time.time()
        duration_ms = int((self.end_time - self.start_time) * 1000)
        telemetry.push_telemetry_event_trained(
            duration_ms,
            self.address_eoa,
            get_total_episodes(self.checkpoint_dir),
        )
        self.training_ended.set()

    def start(self):
        self.before_training()
        try:
            _LOG.info("Training started!")
            result = run_train_main(
                mbag_config=self.convert_result["mbag_config"],
                rllib_path=self.convert_result["out_dir"],
                num_training_iters=self.num_training_iters,
            )
            self.model_dir = result["final_checkpoint"]
        except KeyboardInterrupt:
            _LOG.info("Training stopped!")

        self.after_training()
