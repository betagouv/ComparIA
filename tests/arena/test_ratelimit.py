"""
Unit tests for the input-character budgets (no network, no real Redis).

Four budgets run at once: pricey models and the whole pool, each counted per
anonymous session and per IP. The session budget is the one that matters, since
users behind a shared NAT each get their own; the IP one is only there to catch
a client that drops the session cookie to get a fresh budget.

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_ratelimit.py
"""

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import backend.arena.session as session
from backend.arena.session import (
    RATELIMIT_ALL_MODELS_INPUT,
    RATELIMIT_PRICEY_MODELS_INPUT_PER_IP,
)
from backend.config import RATELIMIT_PRICEY_MODELS_INPUT


class FakeRedis:
    """Minimal string-counter stub matching decode_responses=True behaviour."""

    def __init__(self):
        self.store: dict[str, int] = {}

    def incrby(self, key, amount):
        self.store[key] = self.store.get(key, 0) + amount

    def expire(self, key, ttl):
        pass

    def get(self, key):
        v = self.store.get(key)
        return None if v is None else str(v)


@contextlib.contextmanager
def fake_redis():
    orig = session.get_redis_client
    fake = FakeRedis()
    session.get_redis_client = lambda: fake
    try:
        yield
    finally:
        session.get_redis_client = orig


def test_under_threshold_not_limited():
    with fake_redis():
        session.increment_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 2, pricey=True
        )
        # exactly 2x is not over (check is strictly greater-than)
        assert session.is_ratelimited("sess-a", "1.1.1.1") is False


def test_over_threshold_is_limited():
    with fake_redis():
        session.increment_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 2 + 1, pricey=True
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True


def test_budget_is_per_session_not_shared():
    with fake_redis():
        # One session blows its budget; a second (same IP, different cookie) is
        # clean, as long as the IP backstop is nowhere near spent.
        session.increment_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 3, pricey=True
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True
        assert session.is_ratelimited("sess-b", "1.1.1.1") is False


def test_dropping_the_cookie_does_not_reset_the_budget():
    """The point of the IP backstop: a fresh session every request used to buy a
    fresh budget every request."""
    with fake_redis():
        spent = 0
        n = 0
        while spent <= RATELIMIT_PRICEY_MODELS_INPUT_PER_IP:
            session.increment_input_chars(
                f"sess-{n}", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT, pricey=True
            )
            spent += RATELIMIT_PRICEY_MODELS_INPUT
            n += 1

        # Every one of those sessions was under its own budget.
        assert session.is_ratelimited("brand-new-session", "1.1.1.1") is True
        # A different IP is untouched.
        assert session.is_ratelimited("brand-new-session", "2.2.2.2") is False


def test_cheap_models_are_counted_too():
    """Only pricey models used to be counted, so everything else was free."""
    with fake_redis():
        session.increment_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_ALL_MODELS_INPUT + 1, pricey=False
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True


def test_a_cheap_message_does_not_spend_the_pricey_budget():
    with fake_redis():
        session.increment_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 3, pricey=False
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is False


def test_unknown_key_not_limited():
    with fake_redis():
        assert session.is_ratelimited("never-seen", "9.9.9.9") is False


def run():
    test_under_threshold_not_limited()
    test_over_threshold_is_limited()
    test_budget_is_per_session_not_shared()
    test_dropping_the_cookie_does_not_reset_the_budget()
    test_cheap_models_are_counted_too()
    test_a_cheap_message_does_not_spend_the_pricey_budget()
    test_unknown_key_not_limited()
    print("All rate limit cases passed.")


if __name__ == "__main__":
    run()
