"""
Comparisons an admin sets aside for a partner's evaluation.

An evaluation set is only worth something if the models it tests have never
seen it, so a reserved comparison stays out of the open dataset and goes to
the destinations receiving the reserved one. The raw dataset, which never
leaves for a public place, keeps it like any other.

Reserving is meant to last. Undoing it puts the comparison back in the open
dataset at the next run, which spoils it for a partner who already has it.

What was ever sent is kept in publish_sending, apart from the destinations an
admin can edit or delete. A run records each dataset there before it reads a
single comparison, and closes it once done. A reservation checks that history
and writes in one transaction, holding the same lock a run holds to record its
start: either the reservation lands first and the run reads the comparison as
reserved, or the run is recorded first and the reservation sees it going.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal, NamedTuple, Protocol

from sqlalchemy import false, text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import col, func, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings
from utils.database.models import Comparison
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

# Why a comparison cannot be reserved. Machine-readable: the admin panel
# translates them.
ReserveBlock = Literal["publishing", "published", "pii", "cohort", "not_analyzed"]


class CannotReserveError(Exception):
    def __init__(self, reason: ReserveBlock):
        self.reason = reason
        super().__init__(reason)


class Reservable(Protocol):
    created_at: datetime
    cohorts: str | None
    llm_analyzed: bool | None
    contains_pii: bool | None


class ReservationState(NamedTuple):
    # Whether a run is sending the open dataset. It may be reading a
    # comparison as not reserved.
    publishing: bool
    # What the open dataset and the partner may have received, on the scale
    # of Comparison.created_at.
    open_sent_until: datetime | None
    reserved_sent_until: datetime | None

    def block(self, comparison: Reservable) -> ReserveBlock | None:
        if self.publishing:
            return "publishing"
        if self.open_sent_until and comparison.created_at <= self.open_sent_until:
            return "published"
        if comparison.contains_pii:
            return "pii"
        if comparison.cohorts:
            return "cohort"
        if comparison.llm_analyzed is not True:
            return "not_analyzed"
        return None

    def sent(self, reserved_at: datetime | None) -> bool:
        """Whether the partner may already have this reserved comparison."""
        return bool(
            reserved_at
            and self.reserved_sent_until
            and reserved_at <= self.reserved_sent_until
        )


def _as_local(value: datetime | None) -> datetime | None:
    # sent_until is naive UTC, created_at and reserved_at the host's local
    # time (AutoDatetime). Comparing them as they are would let through what
    # a run sent up to a few hours earlier, on a host that is not on UTC.
    if value is None:
        return None
    return value.replace(tzinfo=UTC).astimezone().replace(tzinfo=None)


async def _lock(session: AsyncSession) -> None:
    # Released with the transaction.
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY})


async def _sending(
    session: AsyncSession, dataset: PublishDataset
) -> tuple[bool, datetime | None]:
    """Whether a run is sending the dataset now, and until when it ever sent it."""
    sending, sent_until = (
        await session.exec(
            select(
                func.bool_or(col(PublishSending.sent_until).is_(None)),
                func.max(col(PublishSending.sent_until)),
            ).where(col(PublishSending.dataset) == dataset)
        )
    ).one()
    return bool(sending), _as_local(sent_until)


async def _state(session: AsyncSession) -> ReservationState:
    publishing, open_sent_until = await _sending(session, "normal")
    sending_reserved, reserved_sent_until = await _sending(session, "reserved")
    return ReservationState(
        publishing=publishing,
        open_sent_until=open_sent_until,
        # A run sending the reserved dataset may take anything reserved so far.
        reserved_sent_until=datetime.now() if sending_reserved else reserved_sent_until,
    )


async def reservation_state() -> ReservationState:
    """For display: reserve() checks again, under the lock."""
    async with get_session() as session:
        return await _state(session)


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


async def reserve(comparison_id: uuid.UUID) -> datetime | None:
    """
    The date the comparison was reserved on, or None when there is no such
    comparison. Reserving it again keeps the first date: that is the one that
    tells whether a run sent it.
    """
    async with get_session() as session:
        await _lock(session)
        state = await _state(session)
        comparison = await session.get(Comparison, comparison_id)
        if comparison is None:
            return None
        if comparison.reserved_at is not None:
            return comparison.reserved_at
        if reason := state.block(comparison):
            raise CannotReserveError(reason)
        reserved_at = comparison.reserved_at = datetime.now()
        session.add(comparison)
        await session.commit()
        return reserved_at


async def unreserve(comparison_id: uuid.UUID) -> bool:
    """Whether there was such a comparison. The next run publishes it."""
    async with get_session() as session:
        comparison = await session.get(Comparison, comparison_id)
        if comparison is None:
            return False
        comparison.reserved_at = None
        session.add(comparison)
        await session.commit()
        return True


async def unreserve_all() -> int:
    async with get_session() as session:
        result = await session.exec(
            update(Comparison)
            .where(col(Comparison.reserved_at).is_not(None))
            .values(reserved_at=None)
        )
        await session.commit()
        return result.rowcount


async def reserved_ids() -> list[str]:
    async with get_session() as session:
        ids = await session.exec(
            select(Comparison.id).where(col(Comparison.reserved_at).is_not(None))
        )
        return [str(comparison_id) for comparison_id in ids.all()]


class ReservedCounts(NamedTuple):
    reserved: int
    # Of those, how many the partner may already have.
    sent: int


async def reserved_counts() -> ReservedCounts:
    sent_until = (await reservation_state()).reserved_sent_until
    sent = col(Comparison.reserved_at) <= sent_until if sent_until else false()
    async with get_session() as session:
        counts = await session.exec(
            select(func.count(), func.count().filter(sent)).where(
                col(Comparison.reserved_at).is_not(None)
            )
        )
        return ReservedCounts(*counts.one())
