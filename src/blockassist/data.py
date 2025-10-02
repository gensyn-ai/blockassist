import shutil
import time
import zipfile
from pathlib import Path

from blockassist.distributed.s3 import upload_zip_to_s3
from blockassist.globals import get_logger

_LOG = get_logger()

## Evaluate data utilities.


def get_all_evaluate_dirs(checkpoint_path: Path) -> list[Path]:
    evaluate_dirs = [
        d
        for d in checkpoint_path.iterdir()
        if d.is_dir()
        and d.name.startswith("evaluate_")
        and not d.name.endswith("_zips")
    ]
    return evaluate_dirs


def check_checkpoint_dir(checkpoint_dir):
    checkpoint_path = Path(checkpoint_dir)
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Checkpoint directory does not exist: {checkpoint_path}"
        )

    return checkpoint_path


def backup_evaluate_dirs(checkpoint_dir: str) -> None:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)
    for d in get_all_evaluate_dirs(checkpoint_path):
        evaluate_dir = checkpoint_path / "evaluate"
        backup_path = evaluate_dir / d.name
        if not backup_path.exists():
            _LOG.info(f"Backing up {d} to {backup_path}")
            shutil.copytree(d, backup_path)


def delete_evaluate_dirs(checkpoint_dir: str) -> None:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)
    evaluate_dirs = get_all_evaluate_dirs(checkpoint_path)
    for d in evaluate_dirs:
        _LOG.info(f"Deleting evaluation directory: {d}")
        shutil.rmtree(d)


def delete_evaluate_zips(checkpoint_dir: str) -> None:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)
    evaluate_zips_dir = checkpoint_path / "evaluate_zips"
    if not evaluate_zips_dir.exists():
        _LOG.info(f"No evaluate_zips directory found at {evaluate_zips_dir}")
        return

    for zip_file in evaluate_zips_dir.glob("*.zip"):
        _LOG.info(f"Deleting zip file: {zip_file}")
        zip_file.unlink()


def restore_evaluate_dirs_from_backup(checkpoint_dir: str) -> None:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)
    backup_dir = checkpoint_path / "evaluate"
    if not backup_dir.exists():
        raise FileNotFoundError(f"No backup directory found: {backup_dir}")

    for d in backup_dir.iterdir():
        dest = checkpoint_path / d.name
        if not dest.exists() and d.is_dir():
            _LOG.info(f"Restoring evaluation directory from backup: {d}")
            shutil.copytree(d, dest)


def zip_and_upload_episodes(
    identifier: str,
    checkpoint_dir: str,
    bucket_name: str,
    evaluate_dirs: list[Path]
) -> list[str]:
    """
    Zip specific episode directories and upload them to S3.

    Args:
        identifier: Unique identifier for this user
        checkpoint_dir: Checkpoint directory containing evaluate_ directories
        bucket_name: S3 bucket name for upload
        evaluate_dirs: List of specific evaluate directory paths to process

    Returns:
        List of uploaded zip file S3 URIs
    """
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)

    if not evaluate_dirs:
        raise ValueError("No evaluation directories provided")

    s3_uris = []
    for evaluate_dir in evaluate_dirs:
        # Wait for the directory to be fully created (race condition fix)
        max_wait_seconds = 180
        wait_interval = 0.5
        waited = 0
        
        while not evaluate_dir.exists() and waited < max_wait_seconds:
            _LOG.info(f"Waiting for evaluation directory to be created: {evaluate_dir} (waited {waited:.1f}s/{max_wait_seconds}s)")
            time.sleep(wait_interval)
            waited += wait_interval
        
        if not evaluate_dir.exists():
            raise FileNotFoundError(f"Evaluation directory does not exist after waiting {max_wait_seconds}s: {evaluate_dir}")
        
        _LOG.info(f"Processing evaluation directory: {evaluate_dir}")

        # Create zip file of the directory
        zip_filename = f"{evaluate_dir.name}.zip"
        zip_path = checkpoint_path / "evaluate_zips" / zip_filename
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing zip if it exists
        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in evaluate_dir.rglob("*"):
                if file_path.is_file():
                    # Calculate relative path for the zip
                    arcname = file_path.relative_to(evaluate_dir)
                    zipf.write(file_path, arcname)

        zip_size_mb = zip_path.stat().st_size / 1024 / 1024
        _LOG.info(f"Created zip file: {zip_path} (size: {zip_size_mb:.2f} MB)")

        # Upload to S3
        s3_uri = upload_zip_to_s3(
            str(zip_path), bucket_name, f"{identifier}/{zip_filename}"
        )
        s3_uris.append(s3_uri)

    return s3_uris


def zip_and_upload_all_episodes(
    identifier: str, checkpoint_dir: str, bucket_name: str
) -> list[str]:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)

    # Get all evaluate directories
    evaluate_dirs = get_all_evaluate_dirs(checkpoint_path)
    if not evaluate_dirs:
        raise ValueError(
            f"No timestamped evaluation directories found in {checkpoint_path}"
        )

    return zip_and_upload_episodes(identifier, checkpoint_dir, bucket_name, evaluate_dirs)


def get_total_episodes(checkpoint_dir: str) -> int:
    checkpoint_path = check_checkpoint_dir(checkpoint_dir)

    episode_counts = []
    evaluate_dirs = get_all_evaluate_dirs(checkpoint_path)
    for evaluate_dir in evaluate_dirs:
        # Count valid episode directories as sessions.
        session_count = 0
        try:
            for item in evaluate_dir.iterdir():
                if not (item.is_dir() and item.name.isdigit()):
                    # Not a valid run directory.
                    continue

                required_files = ['config.json', 'episodes.zip', 'metrics.json', 'run.json']
                if all((item / file).exists() for file in required_files):
                    session_count += 1

        except (OSError, PermissionError) as e:
            _LOG.warning(f"Could not access evaluate directory {evaluate_dir}: {e}")

        episode_counts.append(session_count)
        _LOG.debug(f"Found {session_count} sessions in {evaluate_dir.name}")

    return sum(episode_counts)
