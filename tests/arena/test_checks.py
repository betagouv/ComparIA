"""
Unit tests for the prompt checks (mocked HTTP, no DB, no real Redis).

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_checks.py
"""

import asyncio
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx

import backend.arena.checks as checks
import utils.database.prompt_checks as prompt_checks
from backend.config import settings
from utils.database.models.prompt_check import PromptCheck


class FakeRedis:
    def __init__(self):
        self.store: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1

    def delete(self, key):
        self.store.pop(key, None)

    def get(self, key):
        value = self.store.get(key)
        return None if value is None else str(value)

    def setex(self, key, ttl, value):
        self.store[key] = value


class FakeMistral:
    """Records every moderation request and replays a canned score set."""

    def __init__(self, scores=None, error=None):
        self.scores = scores or {}
        self.error = error
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if self.error:
            raise self.error
        return httpx.Response(200, json={"results": [{"category_scores": self.scores}]})


@contextlib.contextmanager
def arena(rows, scores=None, error=None, redis=None):
    fake = FakeMistral(scores, error)
    redis = redis if redis is not None else FakeRedis()
    orig_client = checks.httpx.AsyncClient
    orig_load = checks.get_prompt_checks
    orig_redis = checks.get_redis_client
    orig_key = settings.MISTRAL_API_KEY

    async def get_prompt_checks():
        return rows

    checks.httpx.AsyncClient = lambda **kwargs: orig_client(
        transport=httpx.MockTransport(fake.handler), **kwargs
    )
    checks.get_prompt_checks = get_prompt_checks
    checks.get_redis_client = lambda: redis
    settings.MISTRAL_API_KEY = "test-key"
    try:
        yield fake
    finally:
        checks.httpx.AsyncClient = orig_client
        checks.get_prompt_checks = orig_load
        checks.get_redis_client = orig_redis
        settings.MISTRAL_API_KEY = orig_key


def content_safety(mode="block"):
    return PromptCheck(
        kind="content_safety",
        mode=mode,
        thresholds={"sexual": 0.3, "selfharm": 0.3, "criminal": 0.5},
    )


def pii(mode="warn"):
    return PromptCheck(kind="pii", mode=mode, thresholds={"pii": 0.5})


def run(rows, scores=None, error=None, text="bonjour", redis=None, proceed=False):
    with arena(rows, scores, error, redis) as fake:
        result = asyncio.run(checks.run_prompt_checks(text, proceed=proceed))
    return result, fake


def test_both_off_makes_no_call():
    result, fake = run([content_safety("off"), pii("off")], {"criminal": 1.0})
    assert fake.requests == []
    assert result.as_record() is None
    assert result.block_message is None


def test_one_call_is_shared_by_both_checks():
    result, fake = run([content_safety(), pii()], {"criminal": 1.0, "pii": 0.9})
    assert len(fake.requests) == 1
    assert fake.requests[0]["input"] == ["bonjour"]
    assert fake.requests[0]["model"] == "mistral-moderation-latest"
    assert set(result.as_record()) == {"content_safety", "pii"}


def test_threshold_boundary_blocks_at_equality():
    result, _ = run([content_safety()], {"sexual": 0.3})
    assert result.as_record()["content_safety"]["decision"] == "blocked"

    result, _ = run([content_safety()], {"sexual": 0.29})
    assert result.as_record()["content_safety"]["decision"] == "pass"
    assert result.block_message is None


def test_selfharm_shows_the_3114_message():
    result, _ = run([content_safety()], {"selfharm": 0.8})
    assert result.block_message is checks.SELF_HARM_MESSAGE


def test_other_categories_show_the_generic_message():
    result, _ = run([content_safety()], {"criminal": 0.9})
    assert result.block_message is checks.GENERIC_MESSAGE


def test_warn_does_not_block():
    result, _ = run([content_safety("warn")], {"criminal": 0.9})
    assert result.block_message is None
    assert result.as_record()["content_safety"]["decision"] == "warned"
    assert result.warnings[0].message is checks.GENERIC_MESSAGE


def test_log_records_the_hit_without_blocking():
    result, _ = run([content_safety("log")], {"criminal": 0.9})
    assert result.block_message is None
    record = result.as_record()["content_safety"]
    assert record["decision"] == "logged"
    assert record["scores"]["criminal"] == 0.9


def test_pii_warns_with_its_own_message():
    result, _ = run([pii()], {"pii": 0.92})
    assert result.warnings[0].message is checks.PII_MESSAGE


def test_error_fails_open():
    result, _ = run([content_safety(), pii()], error=httpx.TimeoutException("too slow"))
    assert result.block_message is None
    record = result.as_record()
    assert record["content_safety"]["decision"] == "error"
    assert record["pii"]["decision"] == "error"


def test_failure_streak_counts_then_resets():
    redis = FakeRedis()
    orig_runner, orig_reader = checks.get_redis_client, prompt_checks.get_redis_client
    checks.get_redis_client = lambda: redis
    prompt_checks.get_redis_client = lambda: redis
    try:
        checks._count_failure("pii", failed=True)
        checks._count_failure("pii", failed=True)
        assert prompt_checks.get_consecutive_failures("pii") == 2
        checks._count_failure("pii", failed=False)
        assert prompt_checks.get_consecutive_failures("pii") == 0
    finally:
        checks.get_redis_client = orig_runner
        prompt_checks.get_redis_client = orig_reader


def test_send_anyway_reuses_the_cached_verdict():
    redis = FakeRedis()
    scores = {"pii": 0.92}

    result, fake = run([pii()], scores, redis=redis)
    assert len(fake.requests) == 1
    assert result.pending_warnings

    result, fake = run([pii()], scores, redis=redis, proceed=True)
    assert fake.requests == []
    assert result.pending_warnings == []
    assert result.as_record()["pii"]["user_proceeded"] is True
    assert result.as_record()["pii"]["decision"] == "warned"


def test_tightening_a_check_applies_to_a_cached_prompt():
    """The cache holds scores, not decisions, so an admin who moves a check to
    block while a warning is on screen still gets the block."""
    redis = FakeRedis()
    scores = {"pii": 0.92}

    result, _ = run([pii("warn")], scores, redis=redis)
    assert result.pending_warnings

    result, fake = run([pii("block")], scores, redis=redis, proceed=True)
    assert fake.requests == []
    assert result.block_message == checks.PII_MESSAGE
    assert result.as_record()["pii"]["decision"] == "blocked"


def test_editing_the_prompt_runs_the_check_again():
    redis = FakeRedis()
    scores = {"pii": 0.92}

    run([pii()], scores, text="mon numero est 06 12 34 56 78", redis=redis)
    result, fake = run([pii()], scores, text="un autre message", redis=redis)

    assert len(fake.requests) == 1
    assert result.pending_warnings


def test_a_passing_prompt_is_not_cached():
    redis = FakeRedis()

    run([pii()], {"pii": 0.1}, redis=redis)
    _, fake = run([pii()], {"pii": 0.1}, redis=redis)

    assert len(fake.requests) == 1


def test_user_proceeded_only_on_warnings():
    result, _ = run([content_safety("log")], {"criminal": 0.9})
    assert "user_proceeded" not in result.as_record()["content_safety"]

    result, _ = run([pii()], {"pii": 0.92})
    assert result.as_record()["pii"]["user_proceeded"] is False


def test_warnings_shown_are_counted():
    redis = FakeRedis()
    orig_runner, orig_reader = checks.get_redis_client, prompt_checks.get_redis_client
    checks.get_redis_client = lambda: redis
    prompt_checks.get_redis_client = lambda: redis
    try:
        assert prompt_checks.get_warnings_shown("pii") == 0
        checks.count_warning_shown("pii")
        checks.count_warning_shown("pii")
        assert prompt_checks.get_warnings_shown("pii") == 2
        assert prompt_checks.get_warnings_shown("content_safety") == 0
    finally:
        checks.get_redis_client = orig_runner
        prompt_checks.get_redis_client = orig_reader


def test_moderate_parses_the_response():
    fake = FakeMistral({"pii": 1.0, "criminal": 0.0})
    orig_client = httpx.AsyncClient
    orig_key = settings.MISTRAL_API_KEY
    checks.httpx.AsyncClient = lambda **kwargs: orig_client(
        transport=httpx.MockTransport(fake.handler), **kwargs
    )
    settings.MISTRAL_API_KEY = "test-key"
    try:
        scores = asyncio.run(checks.moderate("06 12 34 56 78", "mistral-moderation-x"))
    finally:
        checks.httpx.AsyncClient = orig_client
        settings.MISTRAL_API_KEY = orig_key

    assert scores == {"pii": 1.0, "criminal": 0.0}
    assert fake.requests[0]["model"] == "mistral-moderation-x"
