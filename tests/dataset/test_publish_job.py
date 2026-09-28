"""
The publish job starts the runs that are due, from what is in the database.

The run itself is replaced by a recording stub: what is under test is which
destinations get one, and what the job leaves behind it.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import psycopg  # noqa: E402
import pytest  # noqa: E402
from sqlmodel import select  # noqa: E402

from utils.database.models.publish import PublishDestination, PublishRun  # noqa: E402
from utils.database.session import get_session  # noqa: E402
from utils.dataset import job  # noqa: E402


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def naive(text: str) -> datetime:
    return at(text).replace(tzinfo=None)


async def add_destination(
    name: str = "destination",
    frequency: str = "daily",
    last_run: str | None = None,
    requested: str | None = None,
    enabled: bool = True,
) -> uuid.UUID:
    async with get_session() as session:
        row = PublishDestination(
            name=name,
            kind="s3",
            config={"kind": "s3"},
            datasets=["normal"],
            enabled=enabled,
            publish_frequency=frequency,
            last_run_started_at=naive(last_run) if last_run else None,
            publish_requested_at=naive(requested) if requested else None,
        )
        destination_id = row.id
        session.add(row)
        await session.commit()
        return destination_id


async def destination(destination_id: uuid.UUID) -> PublishDestination:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        assert row is not None
        return row


@pytest.fixture
def runs(monkeypatch):
    """The destinations the job started a run for, in order."""
    started: list[uuid.UUID] = []

    async def record(destination_id):
        started.append(destination_id)

    monkeypatch.setattr(job, "run_export", record)
    return started


def test_a_destination_due_by_schedule_starts_a_run_and_one_not_due_does_not(
    database, runs
):
    async def scenario():
        due = await add_destination("due", "daily", last_run="2026-08-03T03:00:05")
        await add_destination("done", "daily", last_run="2026-08-04T03:00:05")
        await job.tick(now=at("2026-08-04T10:00:00"))
        assert runs == [due]

    database(scenario)


def test_weekly_is_due_on_monday_and_monthly_on_the_first(database, runs):
    async def scenario():
        weekly = await add_destination(
            "weekly", "weekly", last_run="2026-08-03T03:00:05"
        )
        monthly = await add_destination(
            "monthly", "monthly", last_run="2026-07-01T03:00:05"
        )

        # Sunday the 9th: Monday the 10th has not come, and neither has the 1st.
        await job.tick(now=at("2026-07-31T10:00:00"))
        assert runs == []
        await job.tick(now=at("2026-08-09T10:00:00"))
        assert runs == [monthly]

        runs.clear()
        await job.tick(now=at("2026-08-10T04:00:00"))
        assert runs == [weekly]

    database(scenario)


def test_a_pending_request_starts_a_run_and_is_cleared_when_it_starts(
    database, monkeypatch
):
    async def scenario():
        requested = await add_destination(
            "requested",
            "off",
            last_run="2026-08-04T03:00:05",
            requested="2026-08-04T09:00:00",
        )
        seen = {}

        async def run(destination_id):
            row = await destination(destination_id)
            seen["requested_at"] = row.publish_requested_at
            seen["last_run"] = row.last_run_started_at

        monkeypatch.setattr(job, "run_export", run)
        await job.tick(now=at("2026-08-04T10:00:00"))

        assert seen["requested_at"] is None
        assert seen["last_run"] == naive("2026-08-04T10:00:00")
        assert (await destination(requested)).publish_requested_at is None

    database(scenario)


def test_a_failed_run_is_not_retried_before_the_next_occurrence(database, monkeypatch):
    calls: list[uuid.UUID] = []

    async def fails(destination_id):
        calls.append(destination_id)
        raise RuntimeError("the export blew up")

    monkeypatch.setattr(job, "run_export", fails)

    async def scenario():
        broken = await add_destination(
            "broken", "daily", last_run="2026-08-03T03:00:05"
        )

        await job.tick(now=at("2026-08-04T10:00:00"))
        await job.tick(now=at("2026-08-04T10:10:00"))
        await job.tick(now=at("2026-08-04T23:50:00"))
        assert calls == [broken]

        await job.tick(now=at("2026-08-05T03:10:00"))
        assert calls == [broken, broken]

    database(scenario)


def test_an_occurrence_missed_while_the_job_was_down_is_caught_up_once(database, runs):
    async def scenario():
        late = await add_destination("late", "daily", last_run="2026-08-01T03:00:05")
        await job.tick(now=at("2026-08-04T10:00:00"))
        await job.tick(now=at("2026-08-04T10:10:00"))
        assert runs == [late]

    database(scenario)


def test_the_first_tick_after_the_migration_starts_nothing(database, runs):
    async def scenario():
        # What the migration leaves: the migration time as the last run.
        await add_destination("daily", "daily", last_run="2026-08-04T10:00:00")
        await add_destination("weekly", "weekly", last_run="2026-08-04T10:00:00")
        await add_destination("monthly", "monthly", last_run="2026-08-04T10:00:00")
        await job.tick(now=at("2026-08-04T10:10:00"))
        assert runs == []

    database(scenario)


def test_an_open_run_with_no_lock_holder_is_closed_as_failed_and_the_tick_goes_on(
    database, runs
):
    async def scenario():
        due = await add_destination("due", "daily", last_run="2026-08-03T03:00:05")
        async with get_session() as session:
            session.add(PublishRun(started_at=naive("2026-08-04T03:00:05")))
            await session.commit()

        await job.tick(now=at("2026-08-04T10:00:00"))

        async with get_session() as session:
            rows = await session.exec(select(PublishRun))
            (run,) = rows.all()
        assert run.finished_at is not None
        assert run.succeeded is False
        assert run.error == "The publish job stopped before the run finished"
        assert runs == [due]

    database(scenario)


def test_a_held_lock_makes_the_tick_exit_without_running(database, runs, postgres_uri):
    async def scenario():
        await add_destination("due", "daily", last_run="2026-08-03T03:00:05")
        async with get_session() as session:
            session.add(PublishRun(started_at=naive("2026-08-04T03:00:05")))
            await session.commit()

        with psycopg.connect(postgres_uri, autocommit=True) as holder:
            holder.execute("SELECT pg_advisory_lock(%s)", (job.ADVISORY_LOCK_KEY,))
            await job.tick(now=at("2026-08-04T10:00:00"))

        assert runs == []
        async with get_session() as session:
            rows = await session.exec(select(PublishRun))
            (run,) = rows.all()
        # Someone else is running: their run is not ours to close.
        assert run.finished_at is None

    database(scenario)


def test_no_destination_is_a_quiet_no_op_and_leaves_the_lock_free(
    database, runs, postgres_uri
):
    async def scenario():
        await job.tick(now=at("2026-08-04T10:00:00"))
        await add_destination(
            "disabled", "daily", enabled=False, requested="2026-08-04T09:00:00"
        )
        await job.tick(now=at("2026-08-04T10:00:00"))
        assert runs == []

        with psycopg.connect(postgres_uri, autocommit=True) as other:
            row = other.execute(
                "SELECT pg_try_advisory_lock(%s)", (job.ADVISORY_LOCK_KEY,)
            ).fetchone()
        assert row == (True,)

    database(scenario)


def test_several_due_destinations_run_one_after_another(database, monkeypatch):
    events: list[tuple[str, uuid.UUID]] = []

    async def slow(destination_id):
        events.append(("start", destination_id))
        await asyncio.sleep(0.05)
        events.append(("end", destination_id))

    monkeypatch.setattr(job, "run_export", slow)

    async def scenario():
        first = await add_destination("first", "daily", last_run="2026-08-03T03:00:05")
        second = await add_destination(
            "second", "daily", last_run="2026-08-03T03:00:05"
        )
        await job.tick(now=at("2026-08-04T10:00:00"))
        assert events == [
            ("start", first),
            ("end", first),
            ("start", second),
            ("end", second),
        ]

    database(scenario)


def test_a_failing_destination_does_not_stop_the_next_one(database, monkeypatch):
    calls: list[uuid.UUID] = []

    async def first_fails(destination_id):
        calls.append(destination_id)
        if len(calls) == 1:
            raise RuntimeError("no")

    monkeypatch.setattr(job, "run_export", first_fails)

    async def scenario():
        first = await add_destination("first", "daily", last_run="2026-08-03T03:00:05")
        second = await add_destination(
            "second", "daily", last_run="2026-08-03T03:00:05"
        )
        await job.tick(now=at("2026-08-04T10:00:00"))
        assert calls == [first, second]

    database(scenario)
