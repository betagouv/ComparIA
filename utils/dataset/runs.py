"""
The publish run an instance sees in the admin panel: when it last ran, whether
it worked, and how many comparisons it held back.

The run records itself. The publish job only closes a row a run left open,
which is what a kill or a crash looks like from outside.
"""

import logging
import uuid
from typing import NamedTuple

from sqlmodel import and_, col, desc, func, or_, select

from utils.database.models import Comparison
from utils.database.models.publish import PublishRun
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.database.utils import get_db_comparisons_counts

logger = logging.getLogger("comparia.dataset")

# Longer than the whole error, and the panel shows it as it is.
_ERROR_MAX = 2_000

# What may leave the instance at all, for the public or for a partner: analysed,
# nothing personal, nothing from a cohort that asked us to keep it. The mirror
# of compute.py's own filter.
SHAREABLE = and_(
    col(Comparison.llm_analyzed) == True,  # noqa: E712
    col(Comparison.contains_pii) != True,  # noqa: E712
    # A NULL is what an ordinary visitor's comparison holds, and
    # 'cohorts IN (NULL, '')' is never true of it.
    or_(col(Comparison.cohorts).is_(None), col(Comparison.cohorts) == ""),
)

# What the open dataset keeps: everything analysis cleared that no admin
# reserved. The mirror of compute.py's own filter, and of
# DatasetComparison.excluded.
PUBLISHABLE = and_(
    SHAREABLE,
    col(Comparison.reserved_at).is_(None),
    col(Comparison.archived) == False,  # noqa: E712
    col(Comparison.contains_spam) != True,  # noqa: E712
    # A comparison that went well stores the JSON value null, not SQL NULL,
    # and both mean the same thing to the exporter. Comparing the column to
    # JSONB.NULL asks SQL 'error IS NULL', which no untouched row satisfies:
    # that counted every comparison ever made as held back.
    or_(
        col(Comparison.error).is_(None),
        func.jsonb_typeof(col(Comparison.error)) == "null",
    ),
)

# What the reserved dataset keeps. Spam, errors and archived comparisons go
# too: the partner judges them for itself.
RESERVED = and_(SHAREABLE, col(Comparison.reserved_at).is_not(None))


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
    reserved: int | None = None,
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
        run.reserved = reserved
        session.add(run)
        await session.commit()


class DatasetCounts(NamedTuple):
    published: int
    reserved: int
    # Neither published nor reserved.
    held_back: int


async def dataset_counts() -> DatasetCounts:
    counts = await get_db_comparisons_counts(
        {
            "published": PUBLISHABLE,
            "reserved": RESERVED,
            "total": col(Comparison.id) != None,  # noqa: E711
        }
    )
    return DatasetCounts(
        published=counts["published"],
        reserved=counts["reserved"],
        held_back=counts["total"] - counts["published"] - counts["reserved"],
    )


async def last_run() -> PublishRun | None:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishRun).order_by(desc(col(PublishRun.started_at))).limit(1)
        )
        return rows.first()


async def recent_runs(limit: int = 20) -> list[PublishRun]:
    """Recent publication history, shared by all destinations."""
    async with get_session() as session:
        rows = await session.exec(
            select(PublishRun).order_by(desc(col(PublishRun.started_at))).limit(limit)
        )
        return list(rows.all())


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
