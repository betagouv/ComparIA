"""
Unit tests for the cap on one long message sent over and over by any session
(no network, no real Redis).

Run with pytest, or directly:
    uv run python tests/arena/test_repeated_prompt.py
"""

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
from tests.arena.test_ratelimit import fake_redis

LONG = "你是角色扮演场景分析师。" * 100
assert len(LONG) >= RATELIMIT_REPEATED_PROMPT_MIN_CHARS


def test_same_long_prompt_is_refused_past_the_cap():
    with fake_redis():
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR):
            assert session.is_repeated_prompt(LONG) is False
        assert session.is_repeated_prompt(LONG) is True


def test_a_refused_script_stays_refused():
    with fake_redis() as fake:
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR + 1):
            session.is_repeated_prompt(LONG)
        # Refused calls keep counting and push the hour back.
        assert session.is_repeated_prompt(LONG) is True
        assert set(fake.ttl.values()) == {3600}


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
        assert fake.store == {}


def test_an_exempt_cohort_is_never_counted():
    with fake_redis() as fake:
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR * 3):
            assert session.is_repeated_prompt(LONG, "pix") is False
            assert session.is_repeated_prompt(LONG, "other,pix") is False
        assert fake.store == {}
        # The same prompt without the cohort is still counted.
        assert session.is_repeated_prompt(LONG, "") is False
        assert len(fake.store) == 1


def test_different_long_prompts_have_their_own_count():
    with fake_redis():
        for _ in range(RATELIMIT_REPEATED_PROMPT_PER_HOUR + 1):
            session.is_repeated_prompt(LONG)
        assert session.is_repeated_prompt(LONG + " et autre chose") is False


def test_redis_error_fails_open():
    class Broken:
        def incr(self, key):
            raise ConnectionError("Redis went away")

    orig = session.get_redis_client
    session.get_redis_client = lambda: Broken()
    try:
        assert session.is_repeated_prompt(LONG) is False
    finally:
        session.get_redis_client = orig


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
