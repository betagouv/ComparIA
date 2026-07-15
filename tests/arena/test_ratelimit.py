"""
Unit tests for the pricey-model rate limit (no network, no real Redis).

Verifies the budget trips at 2x RATELIMIT_PRICEY_MODELS_INPUT and is keyed on
the identity passed in (the anonymous session hash), so two different sessions
behind the same IP get independent budgets.

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_ratelimit.py
"""

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import backend.arena.session as session
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
        session.increment_input_chars("sess-a", RATELIMIT_PRICEY_MODELS_INPUT * 2)
        # exactly 2x is not over (check is strictly greater-than)
        assert session.is_ratelimited("sess-a") is False


def test_over_threshold_is_limited():
    with fake_redis():
        session.increment_input_chars("sess-a", RATELIMIT_PRICEY_MODELS_INPUT * 2 + 1)
        assert session.is_ratelimited("sess-a") is True


def test_budget_is_per_key_not_shared():
    with fake_redis():
        # One session blows its budget; a second (same IP, different cookie) is clean.
        session.increment_input_chars("sess-a", RATELIMIT_PRICEY_MODELS_INPUT * 3)
        assert session.is_ratelimited("sess-a") is True
        assert session.is_ratelimited("sess-b") is False


def test_unknown_key_not_limited():
    with fake_redis():
        assert session.is_ratelimited("never-seen") is False


def run():
    test_under_threshold_not_limited()
    test_over_threshold_is_limited()
    test_budget_is_per_key_not_shared()
    test_unknown_key_not_limited()
    print("All rate limit cases passed.")


if __name__ == "__main__":
    run()
