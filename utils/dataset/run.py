import logging
import os
import subprocess
from pathlib import Path
from typing import Literal

import cyclopts

from backend.config import CountryPortal
from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import count_dataset_rows, process_dataset
from .queries import Datasets, get_dataset_queries

logger = configure_logger(logging.getLogger("dataset"))


def main(
    export_base_path: Path = UTILS_DIR / "local_dataset",
    country_portal: Literal[CountryPortal, "all"] | None = "all",
    dataset: Literal[Datasets, "all"] | None = "all",
    dry_run: bool = False,
    count: bool = False,
):
    """
    Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

    Parameters
    ----------
    export_base_path: str
        Directory for local export (default: utils/local_dataset)
    country_portal: CountryPortal
        Specific dataset portal to export
    dataset: str
        Specific dataset to export (conversations, votes, reactions, conversations_raw). Default: all
    dry_run: bool
        Skip HuggingFace upload (only export to utils/local_dataset/)
    count: bool
        Display row counts for each dataset without exporting
    """
    country_portal = None if country_portal == "all" else country_portal
    dataset = None if dataset == "all" else dataset

    # If --count flag is set, display counts and exit
    if count:
        count_dataset_rows(country_portal)
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
        dataset_queries = get_dataset_queries(country_portal)

        for dataset_name, query in dataset_queries.items():
            if not dataset or dataset == dataset_name:
                process_dataset(
                    dataset_name,
                    query,
                    country_portal,
                    export_base_path,
                    dry_run=dry_run,
                )

        logger.info("Finished processing all datasets.")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user (Ctrl+C)")
        return


if __name__ == "__main__":
    cyclopts.run(main)
