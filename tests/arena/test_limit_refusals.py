"""
What a message refused on a limit tells the browser: which limit, for whom,
and when it lifts (no network, no real Redis).

It used to be one key, `rate_limited`, whatever the cause and with no time,
so the arena could only say "try again in a few hours".
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.arena.limits as limits  # noqa: E402
import backend.arena.router as router  # noqa: E402
import backend.arena.turn_limits as turn_limits  # noqa: E402
import backend.main as main  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.arena.limits import Allowance, AllowanceSpent, Identity  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.errors import LimitReachedError, limit_reached_handler  # noqa: E402
from tests.arena.fakes import fake_redis  # noqa: E402

WHO = Identity.of("sess-a", "1.1.1.1")


def spent(pool, scope, resets_in):
    identity = WHO.session if scope == "session" else WHO.network
    return Allowance(pool, scope, identity, used=11, limit=10, resets_in=resets_in)


@pytest.mark.parametrize(
    "pool, scope, said",
    [
        ("all", "session", ("allowance_spent", "session")),
        ("all", "network", ("allowance_spent", "network")),
        ("expensive", "session", ("expensive_allowance_spent", "session")),
        ("expensive", "network", ("expensive_allowance_spent", "network")),
    ],
)
def test_each_allowance_has_its_own_key_and_scope(pool, scope, said):
    error = turn_limits.limit_refusal([spent(pool, scope, 600)])
    assert (error.key, error.limit.scope) == said
    assert error.limit.llm_ids == []


def test_the_limit_that_lifts_last_is_the_one_told():
    """That is when the person can go on."""
    error = turn_limits.limit_refusal(
        [spent("expensive", "session", 600), spent("all", "network", 4210)]
    )
    assert (error.key, error.limit.scope) == ("allowance_spent", "network")
    assert error.limit.resets_in == 4210
    lifts = datetime.now(timezone.utc) + timedelta(seconds=4210)
    assert abs(error.limit.resets_at - lifts) < timedelta(seconds=2)


def test_a_limit_with_no_known_reset_is_told_over_one_that_lifts():
    error = turn_limits.limit_refusal(
        [spent("all", "network", None), spent("expensive", "session", 4210)]
    )
    assert (error.key, error.limit.scope) == ("allowance_spent", "network")
    assert (error.limit.resets_in, error.limit.resets_at) == (None, None)


def test_a_refused_reservation_says_when_it_lifts(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_ALL_PER_SESSION", 10)
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 11})
        redis.advance(600)
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(WHO, {"all": 1})

    [allowance] = refusal.value.spent
    assert (allowance.pool, allowance.scope) == ("all", "session")
    assert (allowance.used, allowance.resets_in) == (11, limits.WINDOW_SECONDS - 600)


def client_raising(refused):
    error = LimitReachedError(refused.key, refused.limit)
    app = FastAPI()
    app.add_exception_handler(LimitReachedError, limit_reached_handler)

    @app.post("/send")
    def send():
        raise error

    return TestClient(app)


def test_the_body_keeps_detail_a_string_and_puts_the_limit_beside_it():
    """An object `detail` would break every client that reads it as a key."""
    response = client_raising(
        turn_limits.limit_refusal([spent("all", "network", 4210)])
    ).post("/send")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "4210"
    body = response.json()
    assert body["detail"] == "allowance_spent"
    assert body["limit"]["scope"] == "network"
    assert body["limit"]["resets_in"] == 4210
    assert body["limit"]["llm_ids"] == []
    assert body["limit"]["resets_at"].endswith("Z")


def test_no_retry_after_when_the_reset_is_unknown():
    response = client_raising(
        turn_limits.limit_refusal([spent("all", "session", None)])
    ).post("/send")

    assert "Retry-After" not in response.headers
    assert response.json()["limit"]["resets_at"] is None


def test_the_app_answers_a_limit_with_its_handler():
    assert main.app.exception_handlers[LimitReachedError] is limit_reached_handler


@pytest.mark.parametrize("pool", ["all", "expensive"])
def test_a_refused_send_is_logged_as_a_warning(monkeypatch, pool):
    """Someone reaching their limit is the limit working: an error line, and a
    Sentry event, for each of them would bury the real ones."""
    log = Mock()
    monkeypatch.setattr(router, "logger", log)

    router.limit_reached(
        turn_limits.limit_refusal([spent(pool, "session", 600)]), Mock()
    )

    log.warning.assert_called_once()
    log.error.assert_not_called()
