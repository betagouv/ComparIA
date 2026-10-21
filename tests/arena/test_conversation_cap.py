"""
Unit tests for the conversation caps per IP (no network, no real Redis): all the
conversations an IP starts in a sliding hour, and those with the same pair of
models. Exempt cohorts are never counted.

Run with pytest, or directly:
    uv run python tests/arena/test_conversation_cap.py
"""

import contextlib
import os
import sys
from pathlib import Path
from unittest import mock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import backend.arena.session as session
from backend.config import settings
from tests.arena.test_ratelimit import fake_redis

TOTAL = 20
SAME = 5
IP = "198.51.100.4"
A, B, C = uuid4(), uuid4(), uuid4()


@contextlib.contextmanager
def caps(total=TOTAL, same=SAME):
    orig = (
        settings.RATELIMIT_CONVERSATIONS_PER_IP_PER_HOUR,
        settings.RATELIMIT_CONVERSATIONS_SAME_MODELS_PER_IP_PER_HOUR,
    )
    settings.RATELIMIT_CONVERSATIONS_PER_IP_PER_HOUR = total
    settings.RATELIMIT_CONVERSATIONS_SAME_MODELS_PER_IP_PER_HOUR = same
    try:
        yield
    finally:
        (
            settings.RATELIMIT_CONVERSATIONS_PER_IP_PER_HOUR,
            settings.RATELIMIT_CONVERSATIONS_SAME_MODELS_PER_IP_PER_HOUR,
        ) = orig


def test_sixth_conversation_with_the_same_models_is_refused():
    with fake_redis(), caps():
        for _ in range(SAME):
            assert session.reserve_conversation(IP, (A, B)) is True
        assert session.reserve_conversation(IP, (A, B)) is False


def test_the_pair_counts_in_either_order():
    with fake_redis(), caps():
        for _ in range(SAME):
            session.reserve_conversation(IP, (A, B))
        assert session.reserve_conversation(IP, (B, A)) is False


def test_other_models_and_other_ips_have_their_own_pair_count():
    with fake_redis(), caps():
        for _ in range(SAME):
            session.reserve_conversation(IP, (A, B))
        assert session.reserve_conversation(IP, (A, C)) is True
        assert session.reserve_conversation("203.0.113.9", (A, B)) is True


def test_the_twenty_first_conversation_is_refused_whatever_the_models():
    with fake_redis(), caps():
        for _ in range(TOTAL):
            assert session.reserve_conversation(IP, (uuid4(), uuid4())) is True
        assert session.reserve_conversation(IP, (uuid4(), uuid4())) is False
        assert session.reserve_conversation("203.0.113.9", (uuid4(), uuid4())) is True


def test_a_refused_conversation_leaves_the_window_as_it_was():
    with fake_redis() as fake, caps():
        for _ in range(SAME):
            session.reserve_conversation(IP, (A, B))
        for _ in range(10):
            assert session.reserve_conversation(IP, (A, B)) is False
        # Only the five allowed ones are stamped, on both counters.
        assert sorted(len(z) for z in fake.zsets.values()) == [SAME, SAME]


def test_the_window_slides_over_the_hour():
    with fake_redis(), caps():
        with mock.patch("backend.arena.session.time.time", return_value=1_000.0):
            for _ in range(SAME):
                session.reserve_conversation(IP, (A, B))
            assert session.reserve_conversation(IP, (A, B)) is False
        with mock.patch("backend.arena.session.time.time", return_value=1_000.0 + 3601):
            assert session.reserve_conversation(IP, (A, B)) is True


def test_an_exempt_cohort_is_never_counted():
    with fake_redis() as fake, caps():
        for _ in range(TOTAL * 2):
            assert session.reserve_conversation(IP, (A, B), "pix") is True
            assert session.reserve_conversation(IP, (A, B), "other,pix") is True
        assert fake.zsets == {}
        assert session.reserve_conversation(IP, (A, B), "") is True


def test_an_unidentified_caller_is_not_counted_together():
    with fake_redis() as fake, caps():
        for _ in range(TOTAL * 2):
            assert session.reserve_conversation("", (A, B)) is True
        assert fake.zsets == {}


def test_a_cap_set_to_zero_is_off():
    with fake_redis(), caps(total=0, same=0):
        for _ in range(TOTAL * 2):
            assert session.reserve_conversation(IP, (A, B)) is True


def test_redis_error_fails_open():
    class Broken:
        def pipeline(self):
            raise ConnectionError("Redis went away")

    orig = session.get_redis_client
    session.get_redis_client = lambda: Broken()
    try:
        with caps():
            assert session.reserve_conversation(IP, (A, B)) is True
    finally:
        session.get_redis_client = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
