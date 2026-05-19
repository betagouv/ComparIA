import logging
from datetime import date, datetime, timedelta
from typing import Literal

import numpy as np
import polars as pl

from utils.utils import db_connection

from .actions import archive_corrupted, archive_spam, archive_unknown_llms, llm_analyze
from .utils import TABLE_NAMES, reset_archived, set_not_archived

logger = logging.getLogger("comparia.db")

ARCHIVED_CONVERSATIONS_QUERY = """
    SELECT
        timestamp,
        archived,
        archived_reason,
        contains_pii,
        contains_spam
    FROM conversations;
"""
ARCHIVED_QUERY = """
    SELECT
        d.archived,
        d.archived_reason,
        d.timestamp,
        c.contains_pii,
        c.contains_spam
    FROM 
        {table_name} d
    JOIN 
        conversations c ON d.conversation_pair_id = c.conversation_pair_id
    ;
"""


async def log_archived(
    *,
    days: int = 0,
    compare: bool = False,
    order_by: Literal[
        "archived_reason",
        "count",
        "total",
        "percent",
        "last_ts",
        "last_n_days_count",
        "last_n_days_total",
        "last_n_days_count_percent",
    ] = "count",
    descending: bool = True,
) -> None:
    """
    Log archived data infos.

    Parameters
    ----------
    days
        Display only archived data infos with timestamp within the last n days.
    compare
        Display global and last n days archived data infos alongside.
    order_by
        Column to sort by.
    descending: bool
        Sort in descending order.
    """
    last_n_date = datetime.combine(date.today(), datetime.min.time()) - timedelta(
        days=days
    )
    last_n_only = not compare and days

    to_fixed_float = lambda x: np.trunc(x * 100) / 100

    with db_connection(stream=True) as conn:
        for table_name in TABLE_NAMES:
            all_items = pl.read_database(
                query=(
                    ARCHIVED_CONVERSATIONS_QUERY
                    if table_name == "conversations"
                    else ARCHIVED_QUERY.format(table_name=table_name)
                ),
                connection=conn,
                schema_overrides={"archived_reason": pl.String},
            )
            all_items = all_items.with_columns(
                archived=pl.col("archived")
                | pl.col("contains_pii")
                | pl.col("contains_spam"),
                archived_reason=pl.when(
                    ~pl.col("archived") & pl.col("contains_pii").eq(True)
                )
                .then(pl.lit("pii"))
                .when(~pl.col("archived") & pl.col("contains_spam").eq(True))
                .then(pl.lit("spam"))
                .otherwise("archived_reason"),
            )

            all_items_count = len(all_items)
            last_items_count = len(all_items.filter(pl.col("timestamp") > last_n_date))

            last_n_days_count = (
                pl.col("timestamp").filter(pl.col("timestamp") > last_n_date).len()
            )
            reason_count = pl.col("archived_reason").len()
            cols = {f"last_n_days_{col}": col for col in ["count", "total", "percent"]}

            archived_reasons = (
                all_items.filter(pl.col("archived"))
                .group_by("archived_reason")
                .agg(
                    last_ts=pl.col("timestamp").sort().last().dt.date(),
                    count=reason_count,
                    total=all_items_count,
                    percent=to_fixed_float(reason_count / all_items_count * 100),
                    last_n_days_count=last_n_days_count,
                    last_n_days_total=last_items_count,
                    last_n_days_percent=to_fixed_float(
                        last_n_days_count / last_items_count * 100
                    ),
                )
                .drop(
                    *(
                        cols.values()
                        if last_n_only
                        else (cols.keys() if not days else [])
                    )
                )
                .rename(cols if last_n_only else {})
                .sort(pl.col(order_by), descending=descending)
                .filter(pl.col("count") != 0)
            )

            total = archived_reasons.sum()
            total[0, "archived_reason"] = "TOTAL"
            total[0, "total"] = last_items_count if last_n_only else all_items_count
            if compare and days:
                total[0, "last_n_days_total"] = last_items_count

            final = (
                pl.concat([archived_reasons, total])
                .fill_nan(pl.lit(None))
                .fill_null(pl.lit(""))
            )

            with pl.Config(tbl_cols=-1, tbl_rows=-1, set_tbl_hide_dataframe_shape=True):
                logger.info(
                    f"\nArchived '{table_name}' infos{f' since {last_n_date}' if days else ''}:\n{final}"
                )


async def lint(
    *, fix: bool = False, hard: bool = False, with_llm_analyze: bool = False
):
    """
    Run database linting.
    Checks for spam, corrupted data, unknown LLMs in comparisons.
    Only logs what should be archived if no arg given.

    Parameters
    ----------
    fix:
        Actually archive data by setting `archived`, `archive_reason` and
        `archived_at` fields on not already analyzed data if not given `--hard`.
    hard:
        Resets `archived=FALSE` to `NULL` before running checks to recheck
        everything excepts already archived data.
    with_llm_analyze:
        Run LLM analyze on `archived=FALSE` comparisons.
    """
    start_at = datetime.now()

    if hard:
        await reset_archived()

    await archive_spam(commit=fix)
    await archive_corrupted(commit=fix)
    await archive_unknown_llms(commit=fix and hard)

    if fix:
        await set_not_archived(start_at)
    if fix and with_llm_analyze:
        logger.debug("Running LLM analyze on archived=FALSE comparisons…")
        await llm_analyze()

    await log_archived()
