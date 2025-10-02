import io
import json
from pathlib import Path

from huggingface_hub import HfApi

from blockassist import telemetry
from blockassist.globals import get_logger

_LOG = get_logger()


def _create_readme(model_path: Path, user_id: str | None = None) -> None:
    readme_path = model_path / "README.md"

    # Generate identifier tag from address if provided
    tags = ["gensyn", "blockassist", "gensyn-blockassist", "minecraft"]

    if user_id:
        tags.append(user_id.replace("_", " "))

    # Create YAML front matter with tags
    tags_yaml = "\n".join(f'  - "{tag}"' for tag in tags)
    front_matter = f"""\
---
tags:
{tags_yaml}
---

"""
    body = """\
# Gensyn BlockAssist

Gensyn's BlockAssist is a distributed extension of the paper [AssistanceZero: Scalably Solving Assistance Games](https://arxiv.org/abs/2504.07091).
"""
    readme_path.write_text(front_matter + body, encoding="utf-8")
    _LOG.info(
        f"Created README.md with YAML metadata and tags {tags} at {readme_path!r}"
    )


def upload_to_huggingface(
    model_path: Path,
    user_id: str,
    repo_id: str,
    address_eoa: str,
    hf_token: str | None = None,
    chain_metadata_dict: dict | None = None,
) -> str:
    """Uploads the model directory to HuggingFace.
    Args:
        model_path (Path): Path to the model directory.
        user_id (str): Identifier for the user (e.g., address).
        repo_id (str): HuggingFace repository ID.
        hf_token (str | None): HuggingFace authentication token.
        chain_metadata_dict (dict | None): Optional metadata dictionary to upload.
        address_eoa (str | None): Optional EOA address for additional context.
    Returns:
        str: The git reference of the uploaded model.
    Raises:
        FileNotFoundError: If the model directory does not exist.
        Exception: If the upload fails.
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Model directory does not exist: {model_path}")

    try:
        _create_readme(model_path, user_id=user_id)
        api = HfApi(token=hf_token)
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
        api.upload_folder(repo_id=repo_id, repo_type="model", folder_path=model_path)
        ret = None

        if chain_metadata_dict:
            metadata_json = json.dumps(chain_metadata_dict, indent=2)
            metadata_bytes = io.BytesIO(metadata_json.encode("utf-8"))
            ret = api.upload_file(
                path_or_fileobj=metadata_bytes,
                path_in_repo="gensyn.json",
                repo_id=repo_id,
                repo_type="model",
            )
            _LOG.info("Uploaded metadata dictionary")

        # Calculate total size
        total_size = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
        _LOG.info(
            f"Successfully uploaded model to HuggingFace: {repo_id} with size {total_size / 1024 / 1024:.2f} MB ({ret.oid})"
        )
        telemetry.push_telemetry_event_uploaded(total_size, address_eoa, repo_id)

        if ret:
            return ret.oid
        return None

    except Exception as e:
        _LOG.error(f"Failed to upload model to HuggingFace: {e}", exc_info=True)
        raise
