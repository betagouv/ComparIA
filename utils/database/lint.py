import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal, TypedDict

import numpy as np
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


def log_archived(
    *,
    order_by: Literal[
        "archived_reason",
        "count",
        "total",
        "percent",
        "last_ts",
        "last_n_days_count",
        "last_n_days_total",
        "last_n_days_count_percent",
    ] = "archived_reason",
    descending: bool = True,
    days: int = 0,
) -> None:
    """
    Log archived data infos.
    """
    query = """
        SELECT
            archived,
            archived_reason, 
            timestamp 
        FROM 
            {table_name} 
        ;
    """
    last_n_date = datetime.now() - timedelta(days=days)
    to_fixed_float = lambda x: np.trunc(x * 100) / 100

    with db_connection(stream=True) as conn:
        for table_name in TABLE_NAMES:
            results = pl.read_database(
                query=query.format(table_name=table_name),
                connection=conn,
            )
            last_items_count = len(results.filter(pl.col("timestamp") > last_n_date))
            archived_results = results.filter(pl.col("archived"))

            last_n_days_count = (
                pl.col("timestamp").filter(pl.col("timestamp") > last_n_date).len()
            )
            reason_count = pl.col("archived_reason").len()

            archived_reasons = (
                archived_results.group_by("archived_reason")
                .agg(
                    count=reason_count,
                    total=len(results),
                    percent=to_fixed_float(reason_count / len(results) * 100),
                    last_ts=pl.col("timestamp").sort().last().dt.date(),
                    last_n_days_count=last_n_days_count,
                    last_n_days_total=last_items_count,
                    last_n_days_count_percent=to_fixed_float(
                        last_n_days_count / last_items_count * 100
                    ),
                )
                .sort(pl.col(order_by), descending=descending)
            )

            with pl.Config(tbl_cols=-1, tbl_rows=-1, set_tbl_hide_dataframe_shape=True):
                total = archived_reasons.sum()
                total[0, "archived_reason"] = "TOTAL"
                total[0, "total"] = len(results)
                total[0, "last_n_days_total"] = last_items_count
                final = pl.concat([archived_reasons, total])
                if not days:
                    final = final.drop(
                        "last_n_days_count",
                        "last_n_days_total",
                        "last_n_days_count_percent",
                    )
                logger.info(f"\nArchived '{table_name}' infos:\n{final}")


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

    archive_spam(commit=fix)
    archive_or_fix_country_portal(commit=fix)
    archive_corrupted(commit=fix)
    archive_unknown_llms(commit=fix and hard)
    archive_duplicate(commit=fix)
    archive_not_archived(commit=fix)

    if fix:
        set_not_archived(start_at)

    log_archived()
