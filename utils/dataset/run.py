import logging
import shutil
import uuid
from pathlib import Path
from typing import Literal

import cyclopts

from utils.database.session import use_export_engine
from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import count_dataset_rows, process_datasets
from .models import Datasets
from .publish import (
    LOCAL_NAMES,
    DestinationError,
    NotEnoughDiskError,
    enabled_destinations,
    publish,
)
from .runs import finish_run, open_dataset_counts, start_run

logger = logging.getLogger("comparia.dataset")

# A run rebuilds every dataset from row zero, so it needs room for the whole
# thing twice over. Refusing early beats filling the disk the arena writes to.
FREE_DISK_REQUIRED = 20 * 1024**3


def check_free_disk(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    if free < FREE_DISK_REQUIRED:
        raise NotEnoughDiskError(
            f"Only {free / 1024**3:.1f} GB free under '{path}', "
            f"{FREE_DISK_REQUIRED / 1024**3:.0f} GB needed for a run."
        )


async def main(
    *,
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: Literal[Datasets, "all"] = "all",
    dry_run: bool = False,
    count: bool = False,
    use_cache: bool = False,
    record: bool = False,
    destination_id: uuid.UUID | None = None,
):
    """
    Export ComparIA datasets from PostgreSQL to the destinations configured in
    the admin panel.

    Parameters
    ----------
    export_base_path: str
        Directory for local export (default: utils/local_dataset)
    dataset: str
        Specific dataset to export (normal, raw). Default: all
    dry_run: bool
        Build the datasets locally and send them nowhere
    count: bool
        Display row counts for each dataset without exporting
    use_cache: bool
        Rebuild the normal dataset from an existing raw parquet instead of the DB
    record: bool
        Record the run in the database, for the admin panel to read. What the
        scheduler passes; off by hand so a local export does not overwrite the
        instance's last run.
    destination_id: UUID | None
        Send only to this destination. Used by per-destination schedules and
        the manual publish action in the admin panel.
    """
    datasets: list[Datasets] = ["normal", "raw"] if dataset == "all" else [dataset]

    # Before the first query: this process reads against a database that is
    # serving the arena.
    use_export_engine()

    if count:
        return await count_dataset_rows(datasets)

    run_id = await start_run() if record else None
    try:
        built = await _export(
            datasets, export_base_path, dry_run, use_cache, destination_id
        )
    except Exception as exc:
        if run_id:
            await finish_run(run_id, error=str(exc))
        raise
    else:
        if run_id:
            # Only a run that rebuilt the open dataset can say what it holds
            # back. One that sent the raw dataset alone leaves the figures
            # blank rather than quoting numbers it did not produce.
            counts = await open_dataset_counts() if "normal" in built else (None, None)
            await finish_run(run_id, published=counts[0], held_back=counts[1])
    finally:
        # The parquet files are the run's, not the instance's: they are what
        # was just published, and they are large. Only the directories a build
        # creates go, never the export root itself, which is a directory in
        # the repository with files of its own.
        if record:
            for name in LOCAL_NAMES.values():
                shutil.rmtree(export_base_path / name, ignore_errors=True)


async def _export(
    datasets: list[Datasets],
    export_base_path: Path,
    dry_run: bool,
    use_cache: bool,
    destination_id: uuid.UUID | None = None,
) -> dict[Datasets, Path]:
    destinations = (
        [] if dry_run else await enabled_destinations(destination_id=destination_id)
    )
    if dry_run:
        logger.info("[DRY RUN] Building locally, sending nothing")
    elif not destinations:
        raise DestinationError(
            "No enabled publish destination. Add one in the admin panel, "
            "or pass --dry-run to build the datasets locally."
        )
    else:
        # Nothing asked for is nothing to build.
        wanted = {d for destination in destinations for d in destination.datasets}
        skipped = [d for d in datasets if d not in wanted]
        datasets = [d for d in datasets if d in wanted]
        if skipped:
            logger.info(
                f"No destination receives {', '.join(skipped)}, not building it"
            )
        if not datasets:
            raise DestinationError(
                "No enabled destination receives the requested datasets."
            )

    if not dry_run and "normal" in datasets:
        # The open dataset only accepts comparisons that deterministic linting
        # classified and the configured reviewer cleared. Both operations are
        # incremental, so an already prepared comparison is not processed or
        # billed again on later publications.
        from utils.database.lint import lint

        logger.info("Preparing comparisons for the open dataset.")
        await lint(fix=True, with_llm_analyze=True)

    check_free_disk(export_base_path)

    built = await process_datasets(datasets, export_base_path, use_cache=use_cache)
    logger.info("Finished processing all datasets.")

    if destinations:
        publish(destinations, built)

    return built


if __name__ == "__main__":
    configure_logger(logger)
    cyclopts.run(main)
