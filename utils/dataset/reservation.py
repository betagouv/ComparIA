"""
Comparisons an admin sets aside for a partner's evaluation.

An evaluation set is only worth something if the models it tests have never
seen it, so a reserved comparison stays out of the open dataset and goes to
the destinations receiving the reserved one. The raw dataset, which never
leaves for a public place, keeps it like any other.

What was ever sent is kept in publish_sending, apart from the destinations an
admin can edit or delete. A run records each dataset there before it reads a
single comparison, and closes it once done.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import col, update
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings
from utils.database.models.publish import PublishDataset, PublishSending
from utils.database.models.utils import utc_now
from utils.database.session import _async_url, get_session

# Not the publish job's, which a run holds from start to end: a reservation
# only has to wait for a run to record its start.
LOCK_KEY = 8_147_232

# Held, shared, by every process sending datasets for as long as it does,
# whether the publish job started it or someone did by hand. The lock goes
# with the connection when the process dies: a sending left open while nobody
# holds it belongs to a run that died.
ALIVE_LOCK_KEY = 8_147_233


async def _lock(session: AsyncSession) -> None:
    # Released with the transaction.
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY})


@asynccontextmanager
async def _own_connection() -> AsyncIterator[AsyncConnection]:
    # Not the pool's: the export needs both of the pool's connections, and
    # this one has to outlive them all.
    engine = create_async_engine(
        _async_url(settings.COMPARIA_DB_URI), poolclass=NullPool
    )
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


@asynccontextmanager
async def sending(datasets: list[PublishDataset]) -> AsyncIterator[None]:
    """
    Record the datasets a run may send before it reads any comparison, and
    close them once it is over, however it ended: a run that failed half way
    may still have sent some files.
    """
    if not datasets:
        yield
        return
    async with _own_connection() as alive:
        await alive.exec_driver_sql(f"SELECT pg_advisory_lock_shared({ALIVE_LOCK_KEY})")
        # The lock belongs to the session and outlives the commit, which keeps
        # the connection from sitting in a transaction for the whole run.
        await alive.commit()
        ids = await _start_sending(datasets)
        try:
            yield
        finally:
            await _finish_sending(ids)


async def close_abandoned_sendings() -> None:
    """Close the sendings of runs whose process died, when no run is going."""
    async with _own_connection() as connection:
        taken = await connection.exec_driver_sql(
            f"SELECT pg_try_advisory_lock({ALIVE_LOCK_KEY})"
        )
        await connection.commit()
        if not taken.scalar():
            return
        # A run starting now waits for the lock, so it cannot be closed early.
        await _finish_sending()


async def _start_sending(datasets: list[PublishDataset]) -> list[uuid.UUID]:
    async with get_session() as session:
        await _lock(session)
        sendings = [
            PublishSending(dataset=dataset, started_at=utc_now())
            for dataset in datasets
        ]
        ids = [sending.id for sending in sendings]
        session.add_all(sendings)
        await session.commit()
        return ids


async def _finish_sending(ids: list[uuid.UUID] | None = None) -> None:
    """Without ids, every sending left open."""
    query = update(PublishSending).where(
        col(PublishSending.sent_until).is_(None)
        if ids is None
        else col(PublishSending.id).in_(ids)
    )
    async with get_session() as session:
        await session.exec(query.values(sent_until=utc_now()))
        await session.commit()
