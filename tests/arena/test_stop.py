"""
Unit tests for stopping a generation (no DB, no Redis, no provider).

Run with pytest, or directly:
    uv run python tests/arena/test_stop.py
"""

import contextlib
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import utils.database.models  # noqa: E402,F401 needed before importing the router
import backend.arena.session as session  # noqa: E402


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    def get(self, key):
        return self.store.get(key)


# Stop flag in Redis


def test_a_stop_is_recorded_while_streaming_and_kept_with_the_same_ttl():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        assert session.is_stop_requested(comparison_id) is False

        assert session.request_comparison_stop(comparison_id) is True
        assert session.is_stop_requested(comparison_id) is True
        assert session.retreive_comparison_metadata(comparison_id).is_streaming
        assert set(redis.ttls.values()) == {session.COMPARISON_METADATA_TTL}


def test_a_stop_after_the_answers_landed_changes_nothing():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=False)
        assert session.request_comparison_stop(comparison_id) is False
        assert session.is_stop_requested(comparison_id) is False

        # Unknown comparison: same answer, no exception.
        assert session.request_comparison_stop(uuid4()) is False
        assert session.is_stop_requested(uuid4()) is False


def test_starting_the_next_turn_clears_a_stale_stop():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        session.request_comparison_stop(comparison_id)
        session.store_comparison_metadata(comparison_id, is_streaming=False)
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        assert session.is_stop_requested(comparison_id) is False


if __name__ == "__main__":
    test_a_stop_is_recorded_while_streaming_and_kept_with_the_same_ttl()
    test_a_stop_after_the_answers_landed_changes_nothing()
    test_starting_the_next_turn_clears_a_stale_stop()
    print("Stop cases passed.")
