"""
Unit tests for the conversation caps per IP (no network, no real Redis): all the
conversations an IP starts in a sliding hour, and those with the same pair of
models. Exempt cohorts are never counted.

Run with pytest, or directly:
    uv run python tests/arena/test_conversation_cap.py
"""

import os
import sys
from pathlib import Path
from unittest import mock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import backend.arena.session as session
from tests.arena.test_ratelimit import fake_redis

TOTAL = 20
SAME = 5
IP = "198.51.100.4"
A, B, C = uuid4(), uuid4(), uuid4()


def reserve(ip, llm_ids, cohorts=None, caps=(TOTAL, SAME)):
    return session.reserve_conversation(ip, llm_ids, caps, cohorts)


def test_sixth_conversation_with_the_same_models_is_refused():
    with fake_redis():
        for _ in range(SAME):
            assert reserve(IP, (A, B)) is True
        assert reserve(IP, (A, B)) is False


def test_the_pair_counts_in_either_order():
    with fake_redis():
        for _ in range(SAME):
            reserve(IP, (A, B))
        assert reserve(IP, (B, A)) is False


def test_other_models_and_other_ips_have_their_own_pair_count():
    with fake_redis():
        for _ in range(SAME):
            reserve(IP, (A, B))
        assert reserve(IP, (A, C)) is True
        assert reserve("203.0.113.9", (A, B)) is True


def test_the_twenty_first_conversation_is_refused_whatever_the_models():
    with fake_redis():
        for _ in range(TOTAL):
            assert reserve(IP, (uuid4(), uuid4())) is True
        assert reserve(IP, (uuid4(), uuid4())) is False
        assert reserve("203.0.113.9", (uuid4(), uuid4())) is True


def test_a_refused_conversation_leaves_the_window_as_it_was():
    with fake_redis() as fake:
        for _ in range(SAME):
            reserve(IP, (A, B))
        for _ in range(10):
            assert reserve(IP, (A, B)) is False
        # Only the five allowed ones are stamped, on both counters.
        assert sorted(len(z) for z in fake.zsets.values()) == [SAME, SAME]


def test_the_window_slides_over_the_hour():
    with fake_redis():
        with mock.patch("backend.arena.session.time.time", return_value=1_000.0):
            for _ in range(SAME):
                reserve(IP, (A, B))
            assert reserve(IP, (A, B)) is False
        with mock.patch("backend.arena.session.time.time", return_value=1_000.0 + 3601):
            assert reserve(IP, (A, B)) is True


def test_an_exempt_cohort_is_never_counted():
    with fake_redis() as fake:
        for _ in range(TOTAL * 2):
            assert reserve(IP, (A, B), "pix") is True
            assert reserve(IP, (A, B), "other,pix") is True
        assert fake.zsets == {}
        assert reserve(IP, (A, B), "") is True


def test_an_unidentified_caller_is_not_counted_together():
    with fake_redis() as fake:
        for _ in range(TOTAL * 2):
            assert reserve("", (A, B)) is True
        assert fake.zsets == {}


def test_a_cap_set_to_zero_is_off():
    with fake_redis():
        for _ in range(TOTAL * 2):
            assert reserve(IP, (A, B), caps=(0, 0)) is True


def test_each_cap_turns_off_on_its_own():
    with fake_redis():
        for _ in range(SAME + 5):
            assert reserve(IP, (A, B), caps=(TOTAL, 0)) is True
    with fake_redis():
        for _ in range(TOTAL):
            assert reserve(IP, (uuid4(), uuid4()), caps=(0, SAME)) is True


def test_the_caps_are_the_ones_passed_in():
    with fake_redis():
        assert reserve(IP, (A, B), caps=(2, 2)) is True
        assert reserve(IP, (A, B), caps=(2, 2)) is True
        assert reserve(IP, (A, B), caps=(2, 2)) is False


def test_redis_error_fails_open():
    class Broken:
        def pipeline(self):
            raise ConnectionError("Redis went away")

    orig = session.get_redis_client
    session.get_redis_client = lambda: Broken()
    try:
        assert reserve(IP, (A, B)) is True
    finally:
        session.get_redis_client = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
