"""Reserving comparisons for a partner, against a real Postgres.

Skipped where Postgres is not installed.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

from pydantic import ValidationError  # noqa: E402

from tests.admin.test_activity import add_comparison, add_llms  # noqa: E402
from utils.database.models import Comparison  # noqa: E402
from utils.database.models.publish import (  # noqa: E402
    PublishDestination,
    PublishDestinationUpsert,
    PublishRun,
)
from utils.database.models.utils import utc_now  # noqa: E402
from utils.database.session import get_session  # noqa: E402
from utils.dataset import reservation  # noqa: E402
from utils.dataset.reservation import CannotReserveError  # noqa: E402
from utils.dataset.runs import dataset_counts  # noqa: E402

SHAREABLE = {"llm_analyzed": True, "contains_pii": False}


async def add_destination(datasets: list[str], sent_until: datetime | None) -> None:
    async with get_session() as session:
        session.add(
            PublishDestination(
                name="/".join(datasets),
                kind="s3",
                config={"kind": "s3", "endpoint": "s3.example.org", "bucket": "b"},
                datasets=datasets,
                sent_until=sent_until,
            )
        )
        await session.commit()


async def reserved_at(comparison_id: uuid.UUID) -> datetime | None:
    async with get_session() as session:
        comparison = await session.get(Comparison, comparison_id)
        assert comparison
        return comparison.reserved_at


@pytest.mark.parametrize(
    "fields, reason",
    [
        ({"contains_pii": True, "llm_analyzed": True}, "pii"),
        ({**SHAREABLE, "cohorts": "pix"}, "cohort"),
        ({**SHAREABLE, "cohorts": "do-not-track"}, "cohort"),
        ({"contains_pii": False}, "not_analyzed"),
    ],
)
def test_what_cannot_leave_cannot_be_reserved(database, fields, reason):
    async def scenario():
        comparison_id = await add_comparison(await add_llms(), **fields)
        with pytest.raises(CannotReserveError) as refused:
            await reservation.reserve(comparison_id)
        assert refused.value.reason == reason
        assert await reserved_at(comparison_id) is None

    database(scenario)


def test_spam_archived_and_errored_comparisons_can_be_reserved(database):
    async def scenario():
        llms = await add_llms()
        for fields in (
            {"contains_spam": True},
            {"archived": True},
            {"error": {"code": "timeout", "message": "timeout"}},
        ):
            comparison_id = await add_comparison(llms, **SHAREABLE, **fields)
            assert await reservation.reserve(comparison_id)

    database(scenario)


def test_what_the_open_dataset_may_have_sent_cannot_be_reserved(database):
    async def scenario():
        llms = await add_llms()
        now = datetime.now()
        before = await add_comparison(
            llms, created_at=now - timedelta(hours=2), **SHAREABLE
        )
        after = await add_comparison(llms, created_at=now, **SHAREABLE)
        await add_destination(["normal"], utc_now() - timedelta(hours=1))
        # Only the open dataset counts: the raw one never goes public.
        await add_destination(["raw"], utc_now())

        with pytest.raises(CannotReserveError) as refused:
            await reservation.reserve(before)
        assert refused.value.reason == "published"
        assert await reservation.reserve(after)

    database(scenario)


def test_nothing_can_be_reserved_while_a_run_is_going(database):
    async def scenario():
        comparison_id = await add_comparison(await add_llms(), **SHAREABLE)
        async with get_session() as session:
            session.add(PublishRun(started_at=utc_now()))
            await session.commit()

        with pytest.raises(CannotReserveError) as refused:
            await reservation.reserve(comparison_id)
        assert refused.value.reason == "publishing"

    database(scenario)


def test_reserving_again_keeps_the_first_date(database):
    async def scenario():
        comparison_id = await add_comparison(await add_llms(), **SHAREABLE)
        first = await reservation.reserve(comparison_id)
        # Even once the open dataset went out: it was reserved by then.
        await add_destination(["normal"], utc_now())
        assert await reservation.reserve(comparison_id) == first

    database(scenario)


def test_a_missing_comparison_is_neither_reserved_nor_unreserved(database):
    async def scenario():
        assert await reservation.reserve(uuid.uuid4()) is None
        assert not await reservation.unreserve(uuid.uuid4())

    database(scenario)


def test_the_counts_say_what_the_partner_already_has(database):
    async def scenario():
        llms = await add_llms()
        sent, kept = [await add_comparison(llms, **SHAREABLE) for _ in range(2)]
        await reservation.reserve(sent)
        await add_destination(["reserved"], utc_now())
        await reservation.reserve(kept)

        assert await reservation.reserved_counts() == (2, 1)
        state = await reservation.reservation_state()
        assert state.sent(await reserved_at(sent))
        assert not state.sent(await reserved_at(kept))

        assert await reservation.unreserve_all() == 2
        assert await reservation.reserved_counts() == (0, 0)

    database(scenario)


def test_a_reserved_comparison_leaves_the_open_dataset(database):
    async def scenario():
        llms = await add_llms()
        comparison_id = await add_comparison(llms, **SHAREABLE, contains_spam=False)
        await add_comparison(llms, **SHAREABLE, contains_spam=False)
        await add_comparison(llms, contains_pii=True)
        before = await dataset_counts()
        await reservation.reserve(comparison_id)
        after = await dataset_counts()
        await reservation.unreserve(comparison_id)
        return before, after, await dataset_counts()

    before, after, unreserved = database(scenario)

    assert before == (2, 0, 1)
    assert after == (1, 1, 1)
    assert unreserved == before


def test_a_destination_cannot_receive_both_open_and_reserved():
    config = {"kind": "s3", "endpoint": "e", "bucket": "b", "access_key": "a"}
    with pytest.raises(ValidationError, match="different places"):
        PublishDestinationUpsert(
            name="x", config=config, datasets=["normal", "reserved"]
        )
    assert PublishDestinationUpsert(
        name="x", config=config, datasets=["raw", "reserved"]
    )
