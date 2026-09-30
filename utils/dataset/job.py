"""
The publish job: one tick starts a publish run for every destination that is
due, one after the other, and exits.

Run from a CronJob every few minutes, with the backend image. Nothing here
loops or sleeps: a tick with nothing to do costs one query and returns.

A Postgres advisory lock, taken on a connection of its own, is held for the
whole tick. It keeps two ticks from running at once, whether from the two
release colors or a Job started by hand, and it is how a dead run is told from
a live one: a run still open when the lock is free belongs to a job that died
without closing it.
"""

import logging
from datetime import UTC, datetime

import cyclopts
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import col, select

from backend.config import settings
from utils.database.models.publish import PublishDestination
from utils.database.models.utils import as_naive_utc
from utils.database.session import (
    _async_url,
    get_engine,
    get_session,
    use_export_engine,
)
from utils.logger import configure_logger

from .run import main as run
from .runs import close_unfinished_run
from .schedule import previous_run_at

logger = logging.getLogger("comparia.dataset")

# Any constant will do, as long as every job picks the same one.
ADVISORY_LOCK_KEY = 8_147_231

ORPHAN_RUN_ERROR = "The publish job stopped before the run finished"


async def run_export(destination_id) -> None:
    """One publish run, recorded, sent to that destination only."""
    await run(record=True, destination_id=destination_id)


async def _hold_lock(connection: AsyncConnection) -> bool:
    result = await connection.exec_driver_sql(
        f"SELECT pg_try_advisory_lock({ADVISORY_LOCK_KEY})"
    )
    taken = bool(result.scalar())
    # The lock belongs to the session, not the transaction, so it survives this
    # commit. Without it the connection would sit idle in a transaction for the
    # whole run, and one that old holds vacuum back across the database.
    await connection.commit()
    return taken


async def _release_lock(connection: AsyncConnection) -> None:
    await connection.exec_driver_sql(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_KEY})")
    await connection.commit()


def _is_due(row: PublishDestination, now: datetime) -> bool:
    if not row.enabled:
        return False
    # A request asks for a run whatever the schedule says: it is how a
    # destination that publishes only when asked gets one.
    if row.publish_requested_at is not None:
        return True
    occurrence = previous_run_at(row.publish_frequency, now)
    if occurrence is None:
        return False
    last = row.last_run_started_at
    # A failed run started too, and counts as its occurrence's run: nothing
    # retries it before the next one.
    return last is None or last.replace(tzinfo=UTC) < occurrence


async def _claim(destination_id, now: datetime) -> bool:
    """
    Decide whether the destination is due, and if so take the run: the request
    is cleared and the start recorded before the run begins, so that a run
    that dies is still the run of its occurrence.
    """
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if row is None or not _is_due(row, now):
            return False
        row.publish_requested_at = None
        row.last_run_started_at = as_naive_utc(now)
        session.add(row)
        await session.commit()
        return True


async def tick(now: datetime | None = None) -> None:
    if get_engine() is None or not settings.COMPARIA_DB_URI:
        logger.warning("No database configured, nothing to publish")
        return

    # Not the pool's: the export needs both of the pool's connections for
    # itself, and this one has to outlive them all.
    lock_engine = create_async_engine(
        _async_url(settings.COMPARIA_DB_URI), poolclass=NullPool
    )
    try:
        async with lock_engine.connect() as connection:
            if not await _hold_lock(connection):
                logger.info("Another publish job is running, leaving it to it")
                return
            try:
                # With the lock ours, a run still open cannot be anyone's.
                await close_unfinished_run(ORPHAN_RUN_ERROR)
                await _run_due(now)
            finally:
                await _release_lock(connection)
    finally:
        await lock_engine.dispose()


async def _run_due(now: datetime | None) -> None:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishDestination.id)
            .where(col(PublishDestination.enabled) == True)  # noqa: E712
            .order_by(col(PublishDestination.created_at))
        )
        destination_ids = list(rows.all())

    if not destination_ids:
        logger.info("No enabled publish destination")
        return

    for destination_id in destination_ids:
        # Worked out per destination: the run before this one may have taken
        # hours, long enough for an occurrence to come round.
        if not await _claim(destination_id, now or datetime.now(UTC)):
            continue
        logger.info(f"Publish run starting for destination {destination_id}")
        try:
            await run_export(destination_id)
        except Exception:
            # The run recorded its own failure. The next destination does not
            # pay for this one's.
            logger.exception(f"Publish run failed for destination {destination_id}")
        else:
            logger.info(f"Publish run finished for destination {destination_id}")


async def main() -> None:
    """Start a publish run for every destination that is due, then exit."""
    # Before the first query: the runs read against a database that is serving
    # the arena.
    use_export_engine()
    await tick()


if __name__ == "__main__":
    configure_logger(logger)
    cyclopts.run(main)
