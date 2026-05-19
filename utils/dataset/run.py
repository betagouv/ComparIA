import logging
from pathlib import Path
from typing import Literal

import cyclopts
from huggingface_hub import login

from backend.config import settings
from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import count_dataset_rows, process_datasets
from .models import Datasets

logger = logging.getLogger("comparia.dataset")


async def main(
    *,
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: Literal[Datasets, "all"] = "all",
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
        Specific dataset to export (comparisons, comparisons_raw). Default: all
    dry_run: bool
        Skip HuggingFace upload (only export to utils/local_dataset/)
    count: bool
        Display row counts for each dataset without exporting
    """
    dataset_names: list[Datasets] = (
        ["comparisons", "comparisons_raw"]
        if (not dataset or dataset == "all")
        else [dataset]
    )

    # If --count flag is set, display counts and exit
    if count:
        count_dataset_rows()
        return

    # Authenticate with HuggingFace CLI (skip if dry_run)
    if not dry_run:
        logger.info("Login in to HuggingFace $HF_PUSH_DATASET_KEY")
        login(settings.HF_PUSH_DATASET_KEY)
    else:
        logger.info("[DRY RUN] Skipping HuggingFace authentication")

    try:
        await process_datasets(
            dataset_names,
            str(export_base_path),
            dry_run=dry_run,
        )

        logger.info("Finished processing all datasets.")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user (Ctrl+C)")
    except Exception as exc:
        logger.exception(f"An error occurred while processing datasets: {exc}")


if __name__ == "__main__":
    configure_logger(logger)
    cyclopts.run(main)
