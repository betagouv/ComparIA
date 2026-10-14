"""
What `GET /arena/limits` tells the arena before the person types (no network,
no DB, no real Redis).

It says which allowance is spent, for whom and when it lifts, and which models
are paused, so the picker can grey them out. It never says how much was used:
a school's total behind one IP is not one pupil's to see.
"""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.arena.limits as limits  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.arena.limits import Allowance, LimitStatus  # noqa: E402
from backend.auth.dependencies import require_anonymous  # noqa: E402
from backend.config import settings  # noqa: E402
from tests.arena.fakes import fake_redis  # noqa: E402

SESSION = "c" * 64
ME, NETWORK = f"s:{SESSION}", "ip:testclient"
PRICEY, PRICIER = uuid4(), uuid4()
SPENT = settings.RATELIMIT_ALL_PER_IP + 1


@pytest.fixture
def arena(monkeypatch):
    """The route against a fake Redis. `loads` counts reads of the models."""
    state = SimpleNamespace(loads=0)

    async def get_llms_data():
        state.loads += 1
        return SimpleNamespace(expensive_models=[PRICEY, PRICIER])

    monkeypatch.setattr(arena_router, "get_llms_data", get_llms_data)
    app = FastAPI()
    app.include_router(arena_router.router)
    app.dependency_overrides[require_anonymous] = lambda: SESSION
    with fake_redis(limits) as redis:
        state.redis = redis
        state.client = TestClient(app)
        yield state


def spend(redis, pool, identity, resets_in=limits.WINDOW_SECONDS):
    redis.set(limits.budget_key(pool, identity), SPENT, ex=resets_in)


def lifts_in(seconds):
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def close(when, seconds):
    lifts = datetime.fromisoformat(when)
    return abs(lifts - lifts_in(seconds)) < timedelta(seconds=2)


def test_nothing_spent_says_nothing_and_reads_no_model(arena):
    response = arena.client.get("/arena/limits")

    assert response.status_code == 200
    assert response.json() == {"total": None, "expensive": None, "paused_llms": []}
    assert arena.loads == 0


def test_no_cache_may_keep_it(arena):
    assert arena.client.get("/arena/limits").headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("identity, scope", [(ME, "session"), (NETWORK, "network")])
def test_a_spent_whole_allowance_says_for_whom_and_when_it_lifts(
    arena, identity, scope
):
    spend(arena.redis, "all", identity, resets_in=4210)

    body = arena.client.get("/arena/limits").json()

    assert body["total"]["scope"] == scope
    assert close(body["total"]["resets_at"], 4210)
    assert body["total"]["resets_in"] == 4210
    assert body["expensive"] is None
    assert body["paused_llms"] == []


def test_the_whole_allowance_that_lifts_last_is_told(arena):
    spend(arena.redis, "all", ME, resets_in=600)
    spend(arena.redis, "all", NETWORK, resets_in=4210)

    total = arena.client.get("/arena/limits").json()["total"]

    assert total["scope"] == "network"
    assert close(total["resets_at"], 4210)


@pytest.mark.parametrize("identity", [ME, NETWORK])
def test_a_spent_expensive_allowance_pauses_every_expensive_model(arena, identity):
    spend(arena.redis, "expensive", identity, resets_in=4210)

    body = arena.client.get("/arena/limits").json()

    assert body["total"] is None
    assert body["expensive"]["scope"] == ("session" if identity == ME else "network")
    assert close(body["expensive"]["resets_at"], 4210)
    assert [(p["id"], p["reason"]) for p in body["paused_llms"]] == [
        (str(PRICEY), "allowance"),
        (str(PRICIER), "allowance"),
    ]
    assert all(
        p["until"] == body["expensive"]["resets_at"] for p in body["paused_llms"]
    )


def test_each_expensive_model_is_listed_once_when_both_scopes_are_spent(arena):
    spend(arena.redis, "expensive", ME, resets_in=600)
    spend(arena.redis, "expensive", NETWORK, resets_in=4210)

    body = arena.client.get("/arena/limits").json()

    assert [p["id"] for p in body["paused_llms"]] == [str(PRICEY), str(PRICIER)]
    assert close(body["expensive"]["resets_at"], 4210)


def test_it_never_tells_how_much_was_used(arena):
    """A spent allowance and its reset time, nothing more: no counter, no
    limit, no share, for the session or the network."""
    for pool in limits.POOLS:
        for identity in (ME, NETWORK):
            spend(arena.redis, pool, identity)

    body = arena.client.get("/arena/limits").json()

    assert set(body) == {"total", "expensive", "paused_llms"}
    assert (
        set(body["total"])
        == set(body["expensive"])
        == {
            "scope",
            "resets_at",
            "resets_in",
        }
    )
    assert all(set(p) == {"id", "until", "reason"} for p in body["paused_llms"])
    assert str(SPENT) not in str(body)


def test_it_needs_an_anonymous_session():
    app = FastAPI()
    app.include_router(arena_router.router)

    assert TestClient(app).get("/arena/limits").status_code == 401


def test_it_fails_open_when_redis_is_down(arena):
    """A page that cannot read the limits still loads. The message itself is
    charged, and refused, by `reserve`."""
    arena.redis.pipelines_left = 0

    response = arena.client.get("/arena/limits")

    assert response.status_code == 200
    assert response.json()["paused_llms"] == []


def expensive_spent(resets_in):
    allowance = Allowance("expensive", "session", ME, SPENT, 10, resets_in)
    return LimitStatus((allowance,))


def test_a_full_model_is_listed_as_full_when_that_ends_later():
    midnight = lifts_in(8 * 3600)

    status = arena_router.arena_limits(
        expensive_spent(600), [PRICEY, PRICIER], full={PRICEY: midnight}
    )

    assert [(p.id, p.reason, p.until) for p in status.paused_llms] == [
        (PRICEY, "full", midnight),
        (PRICIER, "allowance", status.expensive.resets_at),
    ]
    assert close(status.expensive.resets_at.isoformat(), 600)


def test_a_full_model_stays_paused_by_the_allowance_when_that_ends_later():
    status = arena_router.arena_limits(
        expensive_spent(4210), [PRICEY], full={PRICEY: lifts_in(60)}
    )

    [paused] = status.paused_llms
    assert (paused.reason, paused.until) == ("allowance", status.expensive.resets_at)


def test_a_full_model_stays_paused_by_an_allowance_with_no_known_end():
    """No known end is the longest pause, not one shorter than midnight."""
    status = arena_router.arena_limits(
        expensive_spent(None), [PRICEY], full={PRICEY: lifts_in(8 * 3600)}
    )

    [paused] = status.paused_llms
    assert (paused.reason, paused.until) == ("allowance", None)


def test_a_full_model_is_paused_with_the_expensive_allowance_left():
    cheap, midnight = uuid4(), lifts_in(3600)

    status = arena_router.arena_limits(
        LimitStatus(()), [PRICEY], full={cheap: midnight}
    )

    assert status.expensive is None
    assert [(p.id, p.reason) for p in status.paused_llms] == [(cheap, "full")]
