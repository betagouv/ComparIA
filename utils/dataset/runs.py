"""
The publish run an instance sees in the admin panel: when it last ran, whether
it worked, and how many comparisons it held back.

The child process records its own run. The scheduler only closes a row the
child left open, which is what a kill or a crash looks like from outside.
"""

import logging
import uuid

from sqlmodel import and_, col, desc, func, or_, select

from utils.database.models import Comparison
from utils.database.models.publish import PublishRun
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.database.utils import get_db_comparisons_counts

logger = logging.getLogger("comparia.dataset")

# Longer than the whole error, and the panel shows it as it is.
_ERROR_MAX = 2_000

# What the open dataset keeps: everything analysis cleared. The mirror of
# compute.py's own filter, and of DatasetComparison.excluded.
PUBLISHABLE = and_(
    col(Comparison.archived) == False,  # noqa: E712
    col(Comparison.llm_analyzed) == True,  # noqa: E712
    col(Comparison.contains_pii) != True,  # noqa: E712
    col(Comparison.contains_spam) != True,  # noqa: E712
    # A comparison that went well stores the JSON value null, not SQL NULL,
    # and both mean the same thing to the exporter. Comparing the column to
    # JSONB.NULL asks SQL 'error IS NULL', which no untouched row satisfies:
    # that counted every comparison ever made as held back.
    or_(
        col(Comparison.error).is_(None),
        func.jsonb_typeof(col(Comparison.error)) == "null",
    ),
    # Same trap as the error column: 'cohorts IN (NULL, '')' is never true of
    # a NULL, which is what an ordinary visitor's comparison holds.
    or_(col(Comparison.cohorts).is_(None), col(Comparison.cohorts) == ""),
)


async def start_run() -> uuid.UUID:
    async with get_session() as session:
        run = PublishRun(started_at=utc_now())
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run.id


async def finish_run(
    run_id: uuid.UUID,
    *,
    error: str | None = None,
    published: int | None = None,
    held_back: int | None = None,
) -> None:
    async with get_session() as session:
        run = await session.get(PublishRun, run_id)
        if run is None:
            return
        run.finished_at = utc_now()
        run.succeeded = error is None
        run.error = error[:_ERROR_MAX] if error else None
        run.published = published
        run.held_back = held_back
        session.add(run)
        await session.commit()


async def open_dataset_counts() -> tuple[int, int]:
    """How many comparisons the open dataset published, and how many it held back."""
    counts = await get_db_comparisons_counts(
        {"published": PUBLISHABLE, "total": col(Comparison.id) != None}  # noqa: E711
    )
    return counts["published"], counts["total"] - counts["published"]


async def last_run() -> PublishRun | None:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishRun).order_by(desc(col(PublishRun.started_at))).limit(1)
        )
        return rows.first()


async def close_unfinished_run(reason: str) -> None:
    """
    A run whose process died left its row open. Nothing else will ever close
    it, and an instance reading 'still running' three days later learns
    nothing.
    """
    run = await last_run()
    if run is None or run.finished_at is not None:
        return
    await finish_run(run.id, error=reason)
