"""
The admin panel records Publish requests and starts nothing itself: the
publish job picks them up.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from backend.admin.publishing import router  # noqa: E402
from utils.database.models.publish import PublishDestination, PublishRun  # noqa: E402
from utils.database.models.utils import utc_now  # noqa: E402
from utils.database.session import get_session  # noqa: E402
from utils.dataset.schedule import next_run_at  # noqa: E402

CONFIG = {"kind": "s3", "endpoint": "s3.example.org", "bucket": "b"}
SECRETS = {"access_key": "a", "secret_key": "s"}


def payload(**overrides) -> dict:
    return {
        "name": "Bucket",
        "config": CONFIG | SECRETS,
        "datasets": ["normal"],
        "enabled": True,
        "publish_frequency": "daily",
    } | overrides


def client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(router)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin"
    )


@pytest.fixture(autouse=True)
def nothing_is_started(monkeypatch):
    """
    The panel only writes state. A process started from a request, or from a
    task it left behind, is what this catches: each test ends by giving those
    tasks a moment to run.
    """
    started: list[tuple] = []

    async def record(*args, **kwargs):
        started.append(args)
        raise AssertionError("the panel started a process")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", record)
    yield
    assert started == []


def with_pause(scenario):
    async def paused():
        await scenario()
        await asyncio.sleep(0.1)

    return paused


async def stored(destination_id) -> PublishDestination:
    async with get_session() as session:
        row = await session.get(PublishDestination, uuid.UUID(str(destination_id)))
        assert row is not None
        return row


async def create(api, **overrides) -> dict:
    response = await api.post("/publishing/destinations", json=payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_an_enabled_destination_with_a_frequency_records_a_request(database):
    async def scenario():
        async with client() as api:
            created = await create(api)
        row = await stored(created["id"])
        assert row.publish_requested_at is not None
        assert abs(utc_now() - row.publish_requested_at) < timedelta(minutes=1)

    database(with_pause(scenario))


def test_creating_a_destination_that_is_off_or_disabled_records_no_request(database):
    async def scenario():
        async with client() as api:
            off = await create(api, publish_frequency="off")
            disabled = await create(api, enabled=False)
        assert (await stored(off["id"])).publish_requested_at is None
        assert (await stored(disabled["id"])).publish_requested_at is None

    database(with_pause(scenario))


def test_changing_the_frequency_to_a_non_off_value_records_a_request_and_other_edits_do_not(
    database,
):
    async def scenario():
        async with client() as api:
            created = await create(api, publish_frequency="off")
            url = f"/publishing/destinations/{created['id']}"

            renamed = await api.put(
                url, json=payload(name="Renamed", publish_frequency="off")
            )
            assert renamed.status_code == 200
            assert (await stored(created["id"])).publish_requested_at is None

            changed = await api.put(url, json=payload(publish_frequency="weekly"))
            assert changed.status_code == 200
            assert (await stored(created["id"])).publish_requested_at is not None

    database(with_pause(scenario))


def test_an_edit_that_keeps_the_frequency_or_turns_it_off_records_no_request(database):
    async def scenario():
        async with client() as api:
            created = await create(api, publish_frequency="daily", enabled=False)
            url = f"/publishing/destinations/{created['id']}"

            same = await api.put(
                url, json=payload(name="Renamed", publish_frequency="daily")
            )
            assert same.status_code == 200
            off = await api.put(url, json=payload(publish_frequency="off"))
            assert off.status_code == 200
        assert (await stored(created["id"])).publish_requested_at is None

    database(with_pause(scenario))


def test_publish_now_records_a_request_and_answers_accepted(database):
    async def scenario():
        async with client() as api:
            created = await create(api, publish_frequency="off")
            response = await api.post(
                f"/publishing/destinations/{created['id']}/publish"
            )
        assert response.status_code == 202
        assert (await stored(created["id"])).publish_requested_at is not None

    database(with_pause(scenario))


def test_publish_now_answers_conflict_while_a_run_is_open(database):
    async def scenario():
        async with client() as api:
            created = await create(api, publish_frequency="off")
            async with get_session() as session:
                session.add(PublishRun(started_at=utc_now()))
                await session.commit()
            response = await api.post(
                f"/publishing/destinations/{created['id']}/publish"
            )
        assert response.status_code == 409
        assert (await stored(created["id"])).publish_requested_at is None

    database(with_pause(scenario))


def test_publish_now_answers_unprocessable_when_the_destination_is_disabled(database):
    async def scenario():
        async with client() as api:
            created = await create(api, enabled=False, publish_frequency="off")
            response = await api.post(
                f"/publishing/destinations/{created['id']}/publish"
            )
        assert response.status_code == 422
        assert (await stored(created["id"])).publish_requested_at is None

    database(with_pause(scenario))


def test_the_payload_carries_how_long_a_request_has_been_pending(database):
    async def scenario():
        async with client() as api:
            created = await create(api, publish_frequency="off")
            assert created["request_pending_seconds"] is None

            async with get_session() as session:
                row = await session.get(PublishDestination, uuid.UUID(created["id"]))
                assert row is not None
                row.publish_requested_at = utc_now() - timedelta(minutes=25)
                session.add(row)
                await session.commit()

            listed = (await api.get("/publishing/destinations")).json()["destinations"]
        (destination,) = listed
        assert 25 * 60 <= destination["request_pending_seconds"] < 26 * 60

    database(with_pause(scenario))


def test_the_next_scheduled_run_comes_from_the_shared_schedule(database):
    async def scenario():
        async with client() as api:
            await create(api, publish_frequency="weekly")
            before = datetime.now(UTC)
            listed = (await api.get("/publishing/destinations")).json()["destinations"]
        (destination,) = listed
        assert datetime.fromisoformat(destination["next_run_at"]).replace(
            tzinfo=UTC
        ) == next_run_at("weekly", before)

    database(with_pause(scenario))
