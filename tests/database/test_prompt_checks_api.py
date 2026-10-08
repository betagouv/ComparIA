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

from backend.admin import router as admin_router
from utils.database import prompt_checks as prompt_checks_module
from utils.database.models.prompt_check import (
    DEFAULT_CATEGORIES,
    DEFAULT_MODEL,
    PromptCheck,
    PromptCheckPatch,
)

ADMIN_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def seeded_row() -> PromptCheck:
    return PromptCheck(
        id=1,
        model=DEFAULT_MODEL,
        categories={k: dict(v) for k, v in DEFAULT_CATEGORIES.items()},
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


def full_categories(**overrides: dict) -> dict[str, dict]:
    categories = {k: dict(v) for k, v in DEFAULT_CATEGORIES.items()}
    categories.update(overrides)
    return categories


def test_reads_the_singleton_row(db: FakeSession) -> None:
    row = read_check(db)

    assert row.model == DEFAULT_MODEL
    assert set(row.categories) == set(DEFAULT_CATEGORIES)
    assert row.categories["sexual"] == {"threshold": 0.3, "action": "warn"}


def test_falls_back_to_the_defaults_before_the_row_exists(db: FakeSession) -> None:
    db.row = None

    row = read_check(db)

    assert row.categories == DEFAULT_CATEGORIES


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


def patch_check(body: PromptCheckPatch):
    class CurrentUser:
        id = ADMIN_ID

    return asyncio.run(admin_router.patch_prompt_check(body, CurrentUser()))


def test_patching_categories_replaces_them(
    db: FakeSession, invalidations: list[str]
) -> None:
    categories = full_categories(sexual={"threshold": 0.2, "action": "block"})

    result = patch_check(PromptCheckPatch(categories=categories))

    assert result.categories["sexual"] == {"threshold": 0.2, "action": "block"}
    assert result.updated_by == ADMIN_ID
    assert db.row.categories["sexual"] == {"threshold": 0.2, "action": "block"}


def test_unset_fields_are_left_alone(db: FakeSession, invalidations: list[str]) -> None:
    patch_check(PromptCheckPatch(model="mistral-moderation-2603"))

    assert db.row.model == "mistral-moderation-2603"
    assert db.row.categories == DEFAULT_CATEGORIES


def test_patching_seeds_the_row_when_there_is_none(
    db: FakeSession, invalidations: list[str]
) -> None:
    db.row = None

    result = patch_check(PromptCheckPatch(model="mistral-moderation-2603"))

    assert result.model == "mistral-moderation-2603"
    assert set(result.categories) == set(DEFAULT_CATEGORIES)


def test_write_invalidates_the_cache(db: FakeSession, invalidations: list[str]) -> None:
    patch_check(PromptCheckPatch(model=DEFAULT_MODEL))

    assert invalidations == [prompt_checks_module.REDIS_PROMPT_CHECK_KEY]
    assert db.committed
