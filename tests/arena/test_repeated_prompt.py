"""
Unit tests for the cap on one long message sent over and over by any session
(no network, no real Redis).

Run with pytest, or directly:
    uv run python tests/arena/test_repeated_prompt.py
"""

import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import pytest
from fastapi import HTTPException

import backend.arena.router as router
import backend.arena.session as session
from backend.config import (
    RATELIMIT_REPEATED_PROMPT_MIN_CHARS,
    RATELIMIT_REPEATED_PROMPT_PER_HOUR,
)
from tests.arena.test_ratelimit import FakeRedis, fake_redis

LONG = "你是角色扮演场景分析师。" * 100
assert len(LONG) >= RATELIMIT_REPEATED_PROMPT_MIN_CHARS


@contextlib.contextmanager
def clock(start=1_000_000.0):
    """Freeze the clock the cap reads; set `now[0]` to move it."""
    now = [start]
    orig = session.time
    session.time = SimpleNamespace(time=lambda: now[0])
    try:
        yield now
    finally:
        session.time = orig


def test_same_long_prompt_is_refused_past_the_cap():
    with fake_redis():
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR):
            assert session.is_repeated_prompt(LONG) is False
        assert session.is_repeated_prompt(LONG) is True


def test_a_refused_script_stays_refused():
    with fake_redis() as fake, clock() as now:
        # Once a minute for two hours: refused calls keep counting.
        for _ in range(120):
            now[0] += 60
            refused = session.is_repeated_prompt(LONG)
        assert refused is True
        assert set(fake.ttl.values()) == {3600}
        # Only the stamps past the cap are kept, however long the flood.
        assert [len(z) for z in fake.zsets.values()] == [
            RATELIMIT_REPEATED_PROMPT_PER_HOUR + 1
        ]


def test_a_prompt_sent_now_and_then_is_never_refused():
    with fake_redis(), clock() as now:
        # A template reused all day, but never more than twice in an hour.
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR * 3):
            now[0] += 50 * 60
            assert session.is_repeated_prompt(LONG) is False


def test_the_hour_slides():
    with fake_redis(), clock() as now:
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR):
            assert session.is_repeated_prompt(LONG) is False
        now[0] += 1800
        assert session.is_repeated_prompt(LONG) is True
        # The first burst has left the window, the refused call has not.
        now[0] += 1801
        assert session.is_repeated_prompt(LONG) is False


def test_whitespace_and_case_do_not_buy_a_fresh_count():
    text = "Analyse this scene in eight lines. " * 30
    with fake_redis():
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR):
            session.is_repeated_prompt(text)
        assert session.is_repeated_prompt(f"  {text}\n") is True
        assert session.is_repeated_prompt(text.upper().replace(" ", "  ")) is True


def test_short_prompts_are_never_counted():
    with fake_redis() as fake:
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR * 3):
            assert session.is_repeated_prompt("Hej, hvordan har du det?") is False
        assert fake.zsets == {}


def test_an_exempt_cohort_is_never_counted():
    with fake_redis() as fake:
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR * 3):
            assert session.is_repeated_prompt(LONG, "pix") is False
            assert session.is_repeated_prompt(LONG, "other,pix") is False
        assert fake.zsets == {}
        # The same prompt without the cohort is still counted.
        assert session.is_repeated_prompt(LONG, "") is False
        assert len(fake.zsets) == 1


def test_different_long_prompts_have_their_own_count():
    with fake_redis():
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR + 1):
            session.is_repeated_prompt(LONG)
        assert session.is_repeated_prompt(LONG + " et autre chose") is False


def test_redis_error_fails_open():
    with fake_redis(FakeRedis(pipelines_that_work=0)):
        assert session.is_repeated_prompt(LONG) is False


def test_charge_budget_answers_429_and_spends_nothing():
    llms_data = SimpleNamespace(pricey_models=set())
    request = SimpleNamespace(
        headers={}, client=SimpleNamespace(host="10.2.0.5"), state=SimpleNamespace()
    )
    with fake_redis() as fake:
        for n in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR):
            # Every call a fresh session, as the script does.
            router.charge_budget(LONG, ("a", "b"), llms_data, f"sess-{n}", request)
        spent = {k: v for k, v in fake.store.items() if "pricey_chars" in k}

        with pytest.raises(HTTPException) as exc:
            router.charge_budget(LONG, ("a", "b"), llms_data, "sess-new", request)

        assert exc.value.status_code == 429
        assert exc.value.detail == "rate_limited"
        assert {k: v for k, v in fake.store.items() if "pricey_chars" in k} == spent


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
