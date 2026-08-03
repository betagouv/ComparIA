"""The two admin views on the prompt check: the dry run and the counts.

Mocked HTTP, no DB, no real Redis.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

import backend.arena.checks as checks
from backend.admin import router as admin_router
from utils.database import prompt_checks as prompt_checks_module
from utils.database.models.prompt_check import (
    DEFAULT_CATEGORIES,
    DEFAULT_MODEL,
    PromptCheck,
)


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def incr(self, key):
        self.store[key] = str(int(self.store.get(key, 0)) + 1)

    def delete(self, key):
        self.store.pop(key, None)


def stored_check(**categories) -> PromptCheck:
    merged = {k: dict(v) for k, v in DEFAULT_CATEGORIES.items()}
    merged.update(categories)
    return PromptCheck(
        id=1, model=DEFAULT_MODEL, categories=merged, updated_at=datetime(2026, 1, 1)
    )


def full_categories(**overrides: dict) -> dict[str, dict]:
    categories = {k: dict(v) for k, v in DEFAULT_CATEGORIES.items()}
    categories.update(overrides)
    return categories


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(checks, "get_redis_client", lambda: client)
    monkeypatch.setattr(admin_router.settings, "MISTRAL_API_KEY", "test-key")
    return client


def use_stored(monkeypatch: pytest.MonkeyPatch, check: PromptCheck) -> None:
    async def get_prompt_check():
        return check

    monkeypatch.setattr(admin_router, "get_prompt_check", get_prompt_check)


def stub_moderate(
    monkeypatch: pytest.MonkeyPatch, scores: dict, error: Exception | None = None
) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    async def moderate(text: str, model: str, api_key: str) -> dict:
        calls.append((text, model))
        if error:
            raise error
        return scores

    monkeypatch.setattr(admin_router, "moderate", moderate)
    return calls


def run_try(**body):
    return asyncio.run(
        admin_router.try_prompt_check(admin_router.PromptCheckTryBody(**body))
    )


def test_try_judges_against_unsaved_categories(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    """The stored row only logs pii, the unsaved edit blocks it."""
    use_stored(monkeypatch, stored_check())
    stub_moderate(monkeypatch, {"pii": 0.9})

    result = run_try(
        text="mon numero est 06 12 34 56 78",
        categories=full_categories(pii={"threshold": 0.4, "action": "block"}),
    )

    assert result.decision == "blocked"
    assert result.triggered == {"pii": "block"}
    assert result.message == checks.PII_MESSAGE


def test_try_falls_back_to_the_stored_configuration(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    use_stored(monkeypatch, stored_check(pii={"threshold": 0.5, "action": "warn"}))
    calls = stub_moderate(monkeypatch, {"pii": 0.9})

    result = run_try(text="mon numero est 06 12 34 56 78")

    assert result.decision == "warned"
    assert calls == [("mon numero est 06 12 34 56 78", DEFAULT_MODEL)]


def test_try_uses_the_unsaved_model(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    use_stored(monkeypatch, stored_check())
    calls = stub_moderate(monkeypatch, {"pii": 0.1})

    run_try(text="bonjour", model="mistral-moderation-2603")

    assert calls == [("bonjour", "mistral-moderation-2603")]


def test_try_reports_every_score(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    use_stored(monkeypatch, stored_check())
    stub_moderate(monkeypatch, {"pii": 0.9, "health": 0.7})

    result = run_try(text="bonjour")

    assert result.scores == {"pii": 0.9, "health": 0.7}


def test_try_leaves_the_counters_alone(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    """A dry run that warns must not count a warning, and a successful one must
    not clear a failure streak the arena is reporting."""
    redis.store[checks.REDIS_CHECK_FAILURES_KEY] = "2"
    use_stored(monkeypatch, stored_check(pii={"threshold": 0.5, "action": "warn"}))
    stub_moderate(monkeypatch, {"pii": 0.9})

    result = run_try(text="mon numero est 06 12 34 56 78")

    assert result.decision == "warned"
    assert redis.store[checks.REDIS_CHECK_FAILURES_KEY] == "2"
    assert checks.REDIS_CHECK_WARNINGS_KEY not in redis.store


def test_try_reuses_the_cached_scores(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    """The cache holds scores, so a second threshold on the same text costs no
    second call and still gets its own verdict."""
    use_stored(monkeypatch, stored_check())
    calls = stub_moderate(monkeypatch, {"pii": 0.9})

    first = run_try(
        text="mon numero est 06 12 34 56 78",
        categories=full_categories(pii={"threshold": 0.95, "action": "block"}),
    )
    second = run_try(
        text="mon numero est 06 12 34 56 78",
        categories=full_categories(pii={"threshold": 0.4, "action": "block"}),
    )

    assert len(calls) == 1
    assert first.decision == "pass"
    assert second.decision == "blocked"


def test_try_without_an_api_key_reports_an_error(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    monkeypatch.setattr(admin_router.settings, "MISTRAL_API_KEY", "")
    use_stored(monkeypatch, stored_check())
    calls = stub_moderate(monkeypatch, {"pii": 0.9})

    result = run_try(text="bonjour")

    assert result.decision == "error"
    assert result.scores == {}
    assert result.message == admin_router.NO_API_KEY_MESSAGE
    assert calls == []


def test_try_reports_a_failed_call(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    use_stored(monkeypatch, stored_check())
    stub_moderate(monkeypatch, {}, error=RuntimeError("too slow"))

    result = run_try(text="bonjour")

    assert result.decision == "error"
    assert result.scores == {}
    assert "too slow" in result.message
    assert checks.REDIS_CHECK_FAILURES_KEY not in redis.store


def test_try_rejects_an_unknown_category(
    monkeypatch: pytest.MonkeyPatch, redis: FakeRedis
) -> None:
    with pytest.raises(Exception):
        admin_router.PromptCheckTryBody(
            text="bonjour", categories={"not_a_category": {"threshold": 0.5}}
        )


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def one(self):
        return self.rows


class RecordingSession:
    """Returns canned rows and keeps the SQL each query compiled to."""

    def __init__(self, results):
        self.results = list(results)
        self.queries: list[str] = []

    async def exec(self, query):
        self.queries.append(
            str(
                query.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
        )
        return Rows(self.results.pop(0))


@pytest.fixture
def stats_session(monkeypatch: pytest.MonkeyPatch):
    def install(results) -> RecordingSession:
        session = RecordingSession(results)

        @asynccontextmanager
        async def get_session():
            yield session

        monkeypatch.setattr(prompt_checks_module, "get_session", get_session)
        return session

    return install


DECISION_ROWS = [("pass", 1000), ("logged", 200), ("warned", 30), ("blocked", 4)]


def test_stats_returns_historical_total_period_counts_and_timeline(
    stats_session,
) -> None:
    stats_session(
        [
            1234,
            DECISION_ROWS,
            [("pii", "warned", 22), ("criminal", "blocked", 8)],
            [
                (datetime(2026, 1, 2), "warned", 3),
                (datetime(2026, 1, 2), "blocked", 1),
            ],
        ]
    )

    stats = asyncio.run(prompt_checks_module.get_prompt_check_stats("30d"))

    assert stats == {
        "period": "30d",
        "bucket": "day",
        "historical_total": 1234,
        "total": 1234,
        "by_decision": {
            "pass": 1000,
            "logged": 200,
            "warned": 30,
            "blocked": 4,
            "error": 0,
        },
        "by_category": {
            "pii": {"pass": 0, "logged": 0, "warned": 22, "blocked": 0, "error": 0},
            "criminal": {"pass": 0, "logged": 0, "warned": 0, "blocked": 8, "error": 0},
        },
        "timeline": [
            {
                "date": "2026-01-02",
                "by_decision": {
                    "pass": 0,
                    "logged": 0,
                    "warned": 3,
                    "blocked": 1,
                    "error": 0,
                },
            }
        ],
    }


def test_stats_excludes_the_legacy_guardrail_records(stats_session) -> None:
    """Nemotron records have no decision key, so they are not this check's."""
    session = stats_session([0, DECISION_ROWS, [], []])

    asyncio.run(prompt_checks_module.get_prompt_check_stats("30d"))

    assert len(session.queries) == 4
    for sql in session.queries:
        assert "turn.guardrail ? 'decision'" in sql


def test_stats_period_filters_charts_and_cards_but_not_historical_total(
    stats_session,
) -> None:
    session = stats_session([0, DECISION_ROWS, [], []])

    asyncio.run(prompt_checks_module.get_prompt_check_stats("30d"))

    historical, by_decision, by_category, timeline = session.queries
    assert "turn.created_at >=" not in historical
    assert all(
        "turn.created_at >=" in sql for sql in (by_decision, by_category, timeline)
    )
    assert "date_trunc('day'" in timeline


def test_all_period_is_unbounded_and_monthly(stats_session) -> None:
    session = stats_session([0, [], [], []])

    stats = asyncio.run(prompt_checks_module.get_prompt_check_stats("all"))

    assert stats["bucket"] == "month"
    assert all("turn.created_at >=" not in sql for sql in session.queries)
    assert "date_trunc('month'" in session.queries[3]


def test_invalid_stats_period_falls_back_to_all(stats_session) -> None:
    stats_session([0, [], [], []])

    stats = asyncio.run(prompt_checks_module.get_prompt_check_stats("invalid"))

    assert stats["period"] == "all"


def test_stats_without_a_database_are_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt_checks_module.settings, "COMPARIA_DB_URI", "")
    stats = asyncio.run(prompt_checks_module.get_prompt_check_stats("30d"))

    assert stats["historical_total"] == 0
    assert stats["total"] == 0
    assert stats["by_decision"]["blocked"] == 0
    assert stats["by_category"] == {}
    assert stats["timeline"] == []
