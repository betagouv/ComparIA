"""
Unit tests for the prompt check (mocked HTTP, no DB, no real Redis).

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
from utils.database.models.prompt_check import DEFAULT_CATEGORIES, PromptCheck


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

    def getdel(self, key):
        value = self.get(key)
        self.delete(key)
        return value

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
def arena(check, scores=None, error=None, redis=None):
    fake = FakeMistral(scores, error)
    redis = redis if redis is not None else FakeRedis()
    orig_client = checks.httpx.AsyncClient
    orig_load = checks.get_prompt_check
    orig_redis = checks.get_redis_client
    orig_key = settings.MISTRAL_API_KEY

    async def get_prompt_check():
        return check

    checks.httpx.AsyncClient = lambda **kwargs: orig_client(
        transport=httpx.MockTransport(fake.handler), **kwargs
    )
    checks.get_prompt_check = get_prompt_check
    checks.get_redis_client = lambda: redis
    settings.MISTRAL_API_KEY = "test-key"
    try:
        yield fake
    finally:
        checks.httpx.AsyncClient = orig_client
        checks.get_prompt_check = orig_load
        checks.get_redis_client = orig_redis
        settings.MISTRAL_API_KEY = orig_key


def config(model="mistral-moderation-latest", **categories):
    """A check with every category off except the ones named.

    Each keyword is `category=(threshold, action)`, so a test states only the
    part of the configuration it cares about.
    """
    merged = {c: {"threshold": 0.5, "action": "off"} for c in DEFAULT_CATEGORIES}
    for category, (threshold, action) in categories.items():
        merged[category] = {"threshold": threshold, "action": action}
    return PromptCheck(id=1, model=model, categories=merged)


def run(check, scores=None, error=None, text="bonjour", redis=None, warning_token=None):
    with arena(check, scores, error, redis) as fake:
        result = asyncio.run(checks.run_prompt_check(text, warning_token=warning_token))
    return result, fake


def issued_token(redis, text: str, model: str) -> str:
    token = f"token-{len(redis.store)}"
    redis.setex(
        checks.REDIS_CHECK_WARNING_TOKEN_KEY.format(token=token),
        checks.SCORES_TTL,
        json.dumps({"prompt_hash": checks.hash_content(text), "model": model}),
    )
    return token


def test_everything_off_makes_no_call():
    result, fake = run(config(), {"criminal": 1.0})
    assert fake.requests == []
    assert result is None


def test_one_call_scores_every_category():
    result, fake = run(
        config(criminal=(0.5, "block"), pii=(0.5, "warn")),
        {"criminal": 1.0, "pii": 0.9, "health": 0.7},
    )
    assert len(fake.requests) == 1
    assert fake.requests[0]["input"] == ["bonjour"]
    assert fake.requests[0]["model"] == "mistral-moderation-latest"

    record = result.model_dump()
    assert record["decision"] == "blocked"
    assert record["triggered"] == {"criminal": "block", "pii": "warn"}
    # The never-acted-on categories are still recorded.
    assert record["scores"]["health"] == 0.7


def test_threshold_boundary_triggers_at_equality():
    result, _ = run(config(sexual=(0.3, "block")), {"sexual": 0.3})
    assert result.model_dump()["decision"] == "blocked"

    result, _ = run(config(sexual=(0.3, "block")), {"sexual": 0.29})
    assert result.model_dump()["decision"] == "pass"
    assert result.block_message is None


def test_selfharm_shows_the_3114_message():
    result, _ = run(config(selfharm=(0.3, "block")), {"selfharm": 0.8})
    assert result.block_message is checks.SELF_HARM_MESSAGE


def test_pii_alone_shows_its_own_message():
    result, _ = run(config(pii=(0.5, "warn")), {"pii": 0.92})
    assert result.message is checks.PII_MESSAGE


def test_other_categories_show_the_generic_message():
    result, _ = run(config(criminal=(0.5, "block")), {"criminal": 0.9})
    assert result.block_message is checks.GENERIC_MESSAGE


def test_a_logged_category_does_not_pick_the_message():
    """Only the categories asking for the decision explain it, so a warning on
    pii keeps its own message even when something else is merely logged."""
    result, _ = run(
        config(pii=(0.5, "warn"), criminal=(0.5, "log")),
        {"pii": 0.92, "criminal": 0.9},
    )
    assert result.model_dump()["decision"] == "warned"
    assert result.message is checks.PII_MESSAGE


def test_log_records_the_hit_without_blocking():
    result, _ = run(config(criminal=(0.5, "log")), {"criminal": 0.9})
    assert result.block_message is None
    record = result.model_dump()
    assert record["decision"] == "logged"
    assert record["scores"]["criminal"] == 0.9
    assert record["triggered"] == {"criminal": "log"}


def test_warn_does_not_block():
    result, _ = run(config(criminal=(0.5, "warn")), {"criminal": 0.9})
    assert result.block_message is None
    assert result.pending_warning
    assert result.model_dump()["decision"] == "warned"


def test_error_fails_open():
    result, _ = run(
        config(criminal=(0.5, "block")), error=httpx.TimeoutException("too slow")
    )
    assert result.block_message is None
    record = result.model_dump()
    assert record["decision"] == "error"
    assert record["scores"] == {}


def test_failure_streak_counts_then_resets():
    redis = FakeRedis()
    orig_runner, orig_reader = checks.get_redis_client, prompt_checks.get_redis_client
    checks.get_redis_client = lambda: redis
    prompt_checks.get_redis_client = lambda: redis
    try:
        checks._count_failure(failed=True)
        checks._count_failure(failed=True)
        assert prompt_checks.get_consecutive_failures() == 2
        checks._count_failure(failed=False)
        assert prompt_checks.get_consecutive_failures() == 0
    finally:
        checks.get_redis_client = orig_runner
        prompt_checks.get_redis_client = orig_reader


def test_send_anyway_reuses_the_cached_scores():
    redis = FakeRedis()
    check = config(pii=(0.5, "warn"))
    scores = {"pii": 0.92}

    result, fake = run(check, scores, redis=redis)
    assert len(fake.requests) == 1
    assert result.pending_warning

    token = issued_token(redis, "bonjour", check.model)
    result, fake = run(check, scores, redis=redis, warning_token=token)
    assert fake.requests == []
    assert result.pending_warning is False
    record = result.model_dump()
    assert record["user_proceeded"] is True
    assert record["decision"] == "warned"


def test_tightening_a_category_applies_to_a_cached_prompt():
    """The cache holds scores, not decisions, so an admin who moves a category
    to block while a warning is on screen still gets the block."""
    redis = FakeRedis()
    scores = {"pii": 0.92}

    result, _ = run(config(pii=(0.5, "warn")), scores, redis=redis)
    assert result.pending_warning

    token = issued_token(redis, "bonjour", "mistral-moderation-latest")
    result, fake = run(
        config(pii=(0.5, "block")), scores, redis=redis, warning_token=token
    )
    assert fake.requests == []
    assert result.block_message == checks.PII_MESSAGE
    assert result.model_dump()["decision"] == "blocked"


def test_forged_warning_token_cannot_skip_warning():
    redis = FakeRedis()
    result, fake = run(
        config(pii=(0.5, "warn")),
        {"pii": 0.92},
        redis=redis,
        warning_token="not-issued-by-the-server",
    )
    assert len(fake.requests) == 1
    assert result.pending_warning
    assert result.user_proceeded is False


def test_warning_token_is_bound_to_prompt_and_model_and_cannot_be_replayed():
    redis = FakeRedis()
    check = config(pii=(0.5, "warn"))
    run(check, {"pii": 0.92}, redis=redis)
    token = issued_token(redis, "bonjour", check.model)

    edited, _ = run(
        check, {"pii": 0.92}, text="bonsoir", redis=redis, warning_token=token
    )
    assert edited.pending_warning

    replayed, _ = run(check, {"pii": 0.92}, redis=redis, warning_token=token)
    assert replayed.pending_warning

    other_model = config(model="mistral-moderation-other", pii=(0.5, "warn"))
    other_token = issued_token(redis, "bonjour", check.model)
    changed, fake = run(
        other_model, {"pii": 0.92}, redis=redis, warning_token=other_token
    )
    assert len(fake.requests) == 1
    assert changed.pending_warning


def test_cached_scores_are_isolated_by_model():
    redis = FakeRedis()
    first = config(model="model-a", pii=(0.5, "warn"))
    second = config(model="model-b", pii=(0.5, "warn"))
    run(first, {"pii": 0.92}, redis=redis)

    result, fake = run(second, {"pii": 0.1}, redis=redis)
    assert len(fake.requests) == 1
    assert fake.requests[0]["model"] == "model-b"
    assert result.pending_warning is False


def test_editing_the_prompt_runs_the_check_again():
    redis = FakeRedis()
    check = config(pii=(0.5, "warn"))
    scores = {"pii": 0.92}

    run(check, scores, text="mon numero est 06 12 34 56 78", redis=redis)
    result, fake = run(check, scores, text="un autre message", redis=redis)

    assert len(fake.requests) == 1
    assert result.pending_warning


def test_a_passing_prompt_is_not_cached():
    redis = FakeRedis()
    check = config(pii=(0.5, "warn"))

    run(check, {"pii": 0.1}, redis=redis)
    _, fake = run(check, {"pii": 0.1}, redis=redis)

    assert len(fake.requests) == 1


def test_user_proceeded_only_on_warnings():
    result, _ = run(config(criminal=(0.5, "log")), {"criminal": 0.9})
    assert "user_proceeded" not in result.model_dump()

    result, _ = run(config(pii=(0.5, "warn")), {"pii": 0.92})
    assert result.model_dump()["user_proceeded"] is False


def test_warnings_shown_are_counted():
    redis = FakeRedis()
    orig_runner, orig_reader = checks.get_redis_client, prompt_checks.get_redis_client
    checks.get_redis_client = lambda: redis
    prompt_checks.get_redis_client = lambda: redis
    try:
        assert prompt_checks.get_warnings_shown() == 0
        checks.count_warning_shown()
        checks.count_warning_shown()
        assert prompt_checks.get_warnings_shown() == 2
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
        scores = asyncio.run(
            checks.moderate("06 12 34 56 78", "mistral-moderation-x", "test-key")
        )
    finally:
        checks.httpx.AsyncClient = orig_client
        settings.MISTRAL_API_KEY = orig_key

    assert scores == {"pii": 1.0, "criminal": 0.0}
    assert fake.requests[0]["model"] == "mistral-moderation-x"
