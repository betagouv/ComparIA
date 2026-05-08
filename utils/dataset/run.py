import logging
from pathlib import Path
from typing import Literal

import cyclopts
from huggingface_hub import login

from backend.config import PORTAL_DATASET_INFOS, CountryPortal
from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import count_dataset_rows, process_dataset
from .queries import Datasets, get_dataset_queries

logger = configure_logger(logging.getLogger("dataset"))


def main(
    country_portal: CountryPortal,
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: Literal[Datasets, "all"] | None = "all",
    dry_run: bool = False,
    count: bool = False,
):
    """
    Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

    Parameters
    ----------
    country_portal: CountryPortal
        Specific dataset portal to export
    export_base_path: str
        Directory for local export (default: utils/local_dataset)
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
        logger.info("Login in to HuggingFace $HF_PUSH_DATASET_KEY")
        login(PORTAL_DATASET_INFOS[country_portal]["token"])
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
