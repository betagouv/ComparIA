import logging
from pathlib import Path
from typing import Literal

import cyclopts

from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import count_dataset_rows, process_datasets
from .models import Datasets
from .publish import DestinationError, enabled_destinations, publish

logger = logging.getLogger("comparia.dataset")


async def main(
    *,
    export_base_path: Path = UTILS_DIR / "local_dataset",
    dataset: Literal[Datasets, "all"] = "all",
    dry_run: bool = False,
    count: bool = False,
    use_cache: bool = False,
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
    """
    datasets: list[Datasets] = ["normal", "raw"] if dataset == "all" else [dataset]

    if count:
        return await count_dataset_rows(datasets)

    destinations = [] if dry_run else await enabled_destinations()
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

    built = await process_datasets(datasets, export_base_path, use_cache=use_cache)
    logger.info("Finished processing all datasets.")

    if destinations:
        publish(destinations, built)


if __name__ == "__main__":
    configure_logger(logger)
    cyclopts.run(main)
