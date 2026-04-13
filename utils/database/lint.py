import logging
from collections import defaultdict
from datetime import datetime

import polars as pl

from utils.utils import db_connection

from .actions import (
    archive_corrupted,
    archive_duplicate,
    archive_not_archived,
    archive_or_fix_country_portal,
    archive_spam,
    archive_unknown_llms,
)
from .utils import (
    TABLE_NAMES,
    ArchivedReason,
    TableName,
    reset_archived,
    set_not_archived,
)

logger = logging.getLogger("comparia.database")


def log_archived() -> None:
    query = """
        SELECT archived_reason FROM {table_name} WHERE archived = TRUE;
    """
    archived_counts: dict[ArchivedReason, dict[TableName, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    total_archived_counts: dict[TableName, int] = defaultdict(int)
    with db_connection(stream=True) as conn:
        for table_name in TABLE_NAMES:
            results = pl.read_database(
                query=query.format(table_name=table_name),
                connection=conn,
            )
            total_archived_counts[table_name] = len(results)
            for group in results.group_by("archived_reason").count().to_dicts():
                archived_counts[group["archived_reason"]][table_name] = group["count"]

    total_counts = ", ".join(
        f"{total_archived_counts[table_name]} {table_name}"
        for table_name in TABLE_NAMES
    )
    logger.info(f"Total archived: {total_counts}")
    logger.info("With reason:")
    for reason, tables in archived_counts.items():
        counts = ", ".join(
            f"{count} {table_name}" for table_name, count in tables.items()
        )
        logger.info(f"- '{reason}': {counts}")


def lint(*, fix: bool = False, hard: bool = False):
    """
    Run database linting.

    Will check for spam, corrupted data, unknown LLMs, duplicates and not archived votes or reaction that should be.
    Will only log what should be archived, use `--fix` to actually archive data.
    Will only check not already analyzed data, use `--hard` to analyze/fix all data except already archived data.
    """
    start_at = datetime.now()

    if hard:
        reset_archived()

    # archive_spam(commit=fix) FIXME rm? done in topic_pii.py
    archive_or_fix_country_portal(commit=fix)
    archive_corrupted(commit=fix)
    archive_unknown_llms(commit=fix and hard)
    archive_duplicate(commit=fix)
    archive_not_archived(commit=fix)

    if fix:
        set_not_archived(start_at)

    log_archived()
