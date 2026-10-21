import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

import backend.arena.checks as checks
from backend.admin import router as admin_router
from utils.database import prompt_checks as prompt_checks_module
from utils.database.models.prompt_check import (
    DEFAULT_CRITERIA,
    DEFAULT_MODEL,
    PromptCheck,
    PromptCheckUpsert,
)

ADMIN_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def seeded_row() -> PromptCheck:
    return PromptCheck(
        id=1,
        model=DEFAULT_MODEL,
        criteria=[dict(c) for c in DEFAULT_CRITERIA],
        updated_at=datetime(2026, 1, 1),
    )


class FakeSession:
    """Enough of an async session for the single row this module reads."""

    def __init__(self, row: PromptCheck | None):
        self.row = row
        self.committed = False

    async def get(self, model, key):
        return self.row

    def add(self, row):
        self.row = row

    async def commit(self):
        self.committed = True

    async def refresh(self, row):
        pass


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    session = FakeSession(seeded_row())

    @asynccontextmanager
    async def get_session():
        yield session

    monkeypatch.setattr(prompt_checks_module, "get_session", get_session)
    monkeypatch.setattr(admin_router, "get_consecutive_failures", lambda: 0)
    monkeypatch.setattr(admin_router, "is_key_rejected", lambda: False)
    monkeypatch.setattr(admin_router, "get_warnings_shown", lambda: 0)
    return session


@pytest.fixture
def invalidations(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        prompt_checks_module, "invalidate_cache", lambda key: calls.append(key)
    )
    return calls


def read_check(db: FakeSession) -> PromptCheck:
    return asyncio.run(prompt_checks_module.get_prompt_check.__wrapped__())


def criteria_with(key: str, **changes) -> list[dict]:
    return [c | changes if c["key"] == key else dict(c) for c in DEFAULT_CRITERIA]


def by_key(criteria: list) -> dict[str, dict]:
    """Stored rows hold dicts, API responses hold PromptCheckCriterion."""
    rows = [c if isinstance(c, dict) else c.model_dump() for c in criteria]
    return {c["key"]: c for c in rows}


def test_reads_the_singleton_row(db: FakeSession) -> None:
    row = read_check(db)

    assert row.model == DEFAULT_MODEL
    assert row.criteria == DEFAULT_CRITERIA
    assert by_key(row.criteria)["sexual"]["action"] == "warn"


def test_falls_back_to_the_defaults_before_the_row_exists(db: FakeSession) -> None:
    db.row = None

    row = read_check(db)

    assert row.criteria == DEFAULT_CRITERIA


def test_admin_reading_reports_health(
    db: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def get_prompt_check():
        return seeded_row()

    monkeypatch.setattr(admin_router, "get_prompt_check", get_prompt_check)
    monkeypatch.setattr(
        admin_router,
        "get_consecutive_failures",
        lambda: prompt_checks_module.UNHEALTHY_AFTER_FAILURES,
    )
    monkeypatch.setattr(admin_router, "get_warnings_shown", lambda: 12)

    status = asyncio.run(admin_router.read_prompt_check())

    assert status.healthy is False
    assert status.consecutive_failures == prompt_checks_module.UNHEALTHY_AFTER_FAILURES
    assert status.warnings_shown == 12
    assert status.model == DEFAULT_MODEL


def test_a_working_check_reads_as_healthy(
    db: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def get_prompt_check():
        return seeded_row()

    monkeypatch.setattr(admin_router, "get_prompt_check", get_prompt_check)

    status = asyncio.run(admin_router.read_prompt_check())

    assert status.healthy is True
    assert status.consecutive_failures == 0


def test_a_rejected_key_reads_as_unhealthy(
    db: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def get_prompt_check():
        return seeded_row()

    monkeypatch.setattr(admin_router, "get_prompt_check", get_prompt_check)
    monkeypatch.setattr(admin_router, "is_key_rejected", lambda: True)

    status = asyncio.run(admin_router.read_prompt_check())

    assert status.key_rejected is True
    assert status.healthy is False
    assert status.consecutive_failures == 0


def test_missing_failure_key_counts_as_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    class Client:
        def get(self, key):
            return None

    monkeypatch.setattr(prompt_checks_module, "get_redis_client", lambda: Client())

    assert prompt_checks_module.get_consecutive_failures() == 0


def test_unreachable_redis_counts_as_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom():
        raise RuntimeError("no redis")

    monkeypatch.setattr(prompt_checks_module, "get_redis_client", boom)

    assert prompt_checks_module.get_consecutive_failures() == 0
    assert prompt_checks_module.get_warnings_shown() == 0


class CurrentUser:
    id = ADMIN_ID


def put_check(**changes):
    """Save the seeded form with `changes`, as the admin page sends it whole."""
    seeded = {
        "enabled": True,
        "model": DEFAULT_MODEL,
        "description": "Une arène.",
        "criteria": DEFAULT_CRITERIA,
    }
    body = PromptCheckUpsert(**(seeded | changes))
    return asyncio.run(admin_router.put_prompt_check(body, CurrentUser()))


def test_saving_replaces_the_criteria(
    db: FakeSession, invalidations: list[str]
) -> None:
    result = put_check(criteria=criteria_with("sexual", threshold=0.2, action="block"))

    assert by_key(result.criteria)["sexual"]["action"] == "block"
    assert result.updated_by == ADMIN_ID
    assert by_key(db.row.criteria)["sexual"]["threshold"] == 0.2
    # Stored as plain JSON, not as pydantic objects the column cannot hold.
    assert all(isinstance(c, dict) for c in db.row.criteria)


def test_saving_sets_every_field(db: FakeSession, invalidations: list[str]) -> None:
    put_check(enabled=False, model="perplexity/pplx-decider-flash-v1.2")

    assert db.row.enabled is False
    assert db.row.model == "perplexity/pplx-decider-flash-v1.2"
    assert db.row.description == "Une arène."


@pytest.mark.parametrize("api_key", [None, "", "  "])
def test_a_blank_key_keeps_the_stored_one(
    db: FakeSession, invalidations: list[str], api_key: str | None
) -> None:
    db.row.api_key = "sk-stored"

    result = put_check(api_key=api_key)

    assert db.row.api_key == "sk-stored"
    assert result.has_api_key is True


def test_a_typed_key_replaces_the_stored_one(
    db: FakeSession, invalidations: list[str]
) -> None:
    db.row.api_key = "sk-stored"

    put_check(api_key=" sk-new ")

    assert db.row.api_key == "sk-new"


def test_removing_the_key_falls_back_to_the_environment(
    db: FakeSession, invalidations: list[str]
) -> None:
    db.row.api_key = "sk-stored"

    result = asyncio.run(admin_router.delete_prompt_check_api_key(CurrentUser()))

    assert db.row.api_key is None
    assert result.has_api_key is False
    assert db.row.criteria == DEFAULT_CRITERIA


def test_saving_seeds_the_row_when_there_is_none(
    db: FakeSession, invalidations: list[str]
) -> None:
    db.row = None

    result = put_check(model="perplexity/pplx-decider-flash-v1.2")

    assert result.model == "perplexity/pplx-decider-flash-v1.2"
    assert by_key(result.criteria) == by_key(DEFAULT_CRITERIA)


def test_write_invalidates_the_cache(db: FakeSession, invalidations: list[str]) -> None:
    put_check()

    assert invalidations == [prompt_checks_module.REDIS_PROMPT_CHECK_KEY]
    assert db.committed


def test_the_form_schema_holds_the_criteria() -> None:
    schema = asyncio.run(admin_router.read_prompt_check_schema())

    assert list(schema["properties"]) == [
        "enabled",
        "required",
        "model",
        "api_key",
        "description",
        "criteria",
        "conversations_per_ip_per_hour",
        "conversations_same_models_per_ip_per_hour",
    ]
    criterion = schema["$defs"]["PromptCheckCriterion"]["properties"]
    assert criterion["action"]["enum"] == ["off", "log", "warn", "block"]


class FlagClient:
    def __init__(self):
        self.deleted: list[str] = []

    def delete(self, key):
        self.deleted.append(key)


def test_a_new_key_clears_the_rejected_flag(
    db: FakeSession, invalidations: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FlagClient()
    monkeypatch.setattr(prompt_checks_module, "get_redis_client", lambda: client)

    put_check(api_key="a-new-key")

    assert client.deleted == [prompt_checks_module.REDIS_CHECK_KEY_REJECTED_KEY]


def test_other_changes_leave_the_rejected_flag(
    db: FakeSession, invalidations: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FlagClient()
    monkeypatch.setattr(prompt_checks_module, "get_redis_client", lambda: client)

    put_check(model="perplexity/pplx-decider-flash-v1.2")

    assert client.deleted == []


def test_unset_conversation_caps_report_the_settings_defaults(
    db: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = admin_router.settings
    monkeypatch.setattr(settings, "RATELIMIT_CONVERSATIONS_PER_IP_PER_HOUR", 20)
    monkeypatch.setattr(
        settings, "RATELIMIT_CONVERSATIONS_SAME_MODELS_PER_IP_PER_HOUR", 5
    )

    status = asyncio.run(admin_router.read_prompt_check())

    # Empty in the form, with the default it falls back to beside it.
    assert status.conversations_per_ip_per_hour is None
    assert status.default_conversations_per_ip_per_hour == 20
    assert status.default_conversations_same_models_per_ip_per_hour == 5


def test_saving_the_conversation_caps_stores_them(
    db: FakeSession, invalidations: list[str]
) -> None:
    result = put_check(
        conversations_per_ip_per_hour=50, conversations_same_models_per_ip_per_hour=0
    )

    assert db.row.conversations_per_ip_per_hour == 50
    # Zero is a value of its own, a cap turned off, not a fall back to the default.
    assert db.row.conversations_same_models_per_ip_per_hour == 0
    assert result.conversations_same_models_per_ip_per_hour == 0


def test_an_emptied_cap_goes_back_to_the_default(
    db: FakeSession, invalidations: list[str]
) -> None:
    db.row.conversations_per_ip_per_hour = 50

    put_check(conversations_per_ip_per_hour=None)

    assert db.row.conversations_per_ip_per_hour is None


@pytest.mark.parametrize("value", [-1, 10_001])
def test_a_conversation_cap_out_of_bounds_is_refused(value: int) -> None:
    with pytest.raises(ValueError):
        PromptCheckUpsert(conversations_per_ip_per_hour=value)
    with pytest.raises(ValueError):
        PromptCheckUpsert(conversations_same_models_per_ip_per_hour=value)
