"""
Comparisons an admin sets aside for a partner's evaluation.

An evaluation set is only worth something if the models it tests have never
seen it, so a reserved comparison stays out of the open dataset and goes to
the destinations receiving the reserved one. The raw dataset, which never
leaves for a public place, keeps it like any other.

Reserving is meant to last. Undoing it puts the comparison back in the open
dataset at the next run, which spoils it for a partner who already has it.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal, NamedTuple, Protocol

from sqlalchemy import false
from sqlmodel import col, func, select, update

from utils.database.models import Comparison
from utils.database.models.publish import PublishDataset, PublishDestination
from utils.database.session import get_session

from .runs import last_run

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
    # Whether a run is under way. It may be reading a comparison as not
    # reserved, to send it with the open dataset.
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


async def _sent_until(dataset: PublishDataset) -> datetime | None:
    async with get_session() as session:
        sent_until = await session.exec(
            select(func.max(col(PublishDestination.sent_until))).where(
                col(PublishDestination.datasets).contains([dataset])
            )
        )
        return _as_local(sent_until.one())


async def reservation_state() -> ReservationState:
    run = await last_run()
    return ReservationState(
        publishing=run is not None and run.finished_at is None,
        open_sent_until=await _sent_until("normal"),
        reserved_sent_until=await _sent_until("reserved"),
    )


async def reserve(comparison_id: uuid.UUID) -> datetime | None:
    """
    The date the comparison was reserved on, or None when there is no such
    comparison. Reserving it again keeps the first date: that is the one that
    tells whether a run sent it.
    """
    state = await reservation_state()
    async with get_session() as session:
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
