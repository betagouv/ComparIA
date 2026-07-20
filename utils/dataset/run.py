import logging
import time
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


def purge_expired_export_files(export_base_path: Path, retention_days: int) -> int:
    """Delete generated dataset files older than an explicitly chosen duration."""
    if retention_days < 1:
        raise ValueError("Local export retention must be at least one day")
    if not export_base_path.exists():
        return 0

    cutoff = time.time() - retention_days * 24 * 60 * 60
    deleted = 0
    for path in export_base_path.rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".parquet", ".jsonl", ".tsv"}
            and path.stat().st_mtime < cutoff
        ):
            path.unlink()
            deleted += 1
    return deleted


async def main(
    *,
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: Literal[Datasets, "all"] = "normal",
    dry_run: bool = False,
    count: bool = False,
    use_cache: bool = False,
    allow_raw_publication: bool = False,
    include_unsafe_internal_raw: bool = False,
    local_retention_days: int | None = None,
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
    allow_raw_publication: bool
        Explicitly allow upload of the filtered raw schema. Raw rows that fail
        publication checks remain excluded.
    include_unsafe_internal_raw: bool
        Include rejected rows only in an explicit local raw dry run. Never
        permits upload.
    local_retention_days: int | None
        Remove generated local dataset files older than this many days.
    """
    # "all" is retained for CLI compatibility but now means all datasets that
    # are safe by default. Raw export always requires an explicit selection.
    datasets: list[Datasets] = ["normal"] if dataset == "all" else [dataset]

    if local_retention_days is not None:
        deleted = purge_expired_export_files(export_base_path, local_retention_days)
        logger.info(
            "Expired local dataset files purged",
            extra={"extra": {"event": "dataset.local_purge", "deleted": deleted}},
        )

    # If --count flag is set, display counts and exit
    if count:
        return await count_dataset_rows(datasets)

    if "raw" in datasets and not dry_run and not allow_raw_publication:
        raise ValueError(
            "Raw dataset publication is disabled by default. "
            "Pass --allow-raw-publication after reviewing the destination and data."
        )
    if include_unsafe_internal_raw and (not dry_run or "raw" not in datasets):
        raise ValueError(
            "Unsafe raw rows are restricted to an explicit local raw export "
            "(--dry-run --dataset raw --include-unsafe-internal-raw)."
        )

    # Authenticate with HuggingFace CLI (skip if dry_run)
    if not dry_run:
        logger.info("Login in to HuggingFace $HF_PUSH_DATASET_KEY")
        login(settings.HF_PUSH_DATASET_KEY)
    else:
        logger.info("[DRY RUN] Skipping HuggingFace authentication")

    try:
        await process_datasets(
            datasets,
            export_base_path,
            dry_run=dry_run,
            use_cache=use_cache,
            allow_raw_publication=allow_raw_publication,
            include_unsafe_internal_raw=include_unsafe_internal_raw,
        )

        logger.info("Finished processing all datasets.")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user (Ctrl+C)")
    except Exception as exc:
        logger.exception(f"An error occurred while processing datasets: {exc}")
        raise


if __name__ == "__main__":
    configure_logger(logger)
    cyclopts.run(main)
