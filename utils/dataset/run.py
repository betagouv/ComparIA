import logging
import os
import subprocess
from pathlib import Path

import cyclopts

from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import DATASET_CONFIG, count_dataset_rows, process_dataset

logger = configure_logger(logging.getLogger("dataset.export"))


def main(
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: str | None = None,
    dry_run: bool = False,
    count: bool = False,
):
    """
    Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

    Parameters
    ----------
    export_base_path: str
        Directory for local export (default: utils/local_dataset)
    dataset: str
        Specific dataset to export (conversations, votes, reactions, conversations_raw). Default: all
    dry_run: bool
        Skip HuggingFace upload (only export to utils/local_dataset/)
    count: bool
        Display row counts for each dataset without exporting


    Examples:
        python export_dataset.py ./exports conversations
        python export_dataset.py --dry-run
        python export_dataset.py ./exports --dry-run
    """

    # If --count flag is set, display counts and exit
    if count:
        count_dataset_rows()
        return

    # Log spam detection info
    logger.info("Spam detection enabled for filtering dataset")

    # Authenticate with HuggingFace CLI (skip if dry_run)
    if not dry_run:
        logger.info("hf auth login --token $HF_PUSH_DATASET_KEY")

        _login_result = subprocess.run(
            args=[
                "hf",
                "auth",
                "login",
                "--token",
                os.getenv("HF_PUSH_DATASET_KEY", ""),
            ]
        )

        if _login_result.returncode == 0:
            logger.info("Logged in")
        else:
            logger.error(f"Failed to login: {_login_result.stderr}")
            return False
    else:
        logger.info("[DRY RUN] Skipping HuggingFace authentication")

    if dataset:
        logger.warning(f"only processing dataset: {dataset}")

    # Process each dataset (or just the specified one)
    try:
        for dataset_name, config in DATASET_CONFIG.items():
            if not dataset or dataset == dataset_name:
                process_dataset(dataset_name, config, export_base_path, dry_run=dry_run)

        logger.info("Finished processing all datasets.")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user (Ctrl+C)")
        return


if __name__ == "__main__":
    cyclopts.run(main)
