import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

from backend.admin import router as admin_router
from utils.database import prompt_checks as prompt_checks_module
from utils.database.models.prompt_check import (
    DEFAULT_MODEL,
    DEFAULT_THRESHOLDS,
    PromptCheck,
    PromptCheckPatch,
)

ADMIN_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Enough of an async session for the two queries this module runs."""

    def __init__(self, rows):
        self.rows = rows
        self.committed = False

    async def exec(self, query):
        wanted = _kind_in(query)
        if wanted is None:
            return FakeResult(self.rows)
        return FakeResult([row for row in self.rows if row.kind == wanted])

    def add(self, row):
        pass

    async def commit(self):
        self.committed = True

    async def refresh(self, row):
        pass


def _kind_in(query) -> str | None:
    """Pull the kind out of a `where(kind == ...)` clause, if there is one."""
    clause = query.whereclause
    return None if clause is None else clause.right.value


def seeded_rows() -> list[PromptCheck]:
    return [
        PromptCheck(
            id=index,
            kind=kind,
            mode="log",
            thresholds=dict(thresholds),
            model=DEFAULT_MODEL,
            updated_at=datetime(2026, 1, 1),
        )
        for index, (kind, thresholds) in enumerate(DEFAULT_THRESHOLDS.items(), start=1)
    ]


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    session = FakeSession(seeded_rows())

    @asynccontextmanager
    async def get_session():
        yield session

    monkeypatch.setattr(prompt_checks_module, "get_session", get_session)
    monkeypatch.setattr(admin_router, "get_consecutive_failures", lambda kind: 0)
    return session


@pytest.fixture
def invalidations(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        prompt_checks_module, "invalidate_cache", lambda key: calls.append(key)
    )
    return calls


def read_checks(db: FakeSession):
    async def run():
        return list(await prompt_checks_module.get_prompt_checks.__wrapped__())

    return asyncio.run(run())


def test_reads_both_seeded_rows(db: FakeSession) -> None:
    rows = read_checks(db)

    assert [row.kind for row in rows] == ["content_safety", "pii"]
    assert [row.mode for row in rows] == ["log", "log"]
    assert rows[1].thresholds == {"pii": 0.5}


def test_admin_listing_reports_health_per_check(
    db: FakeSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def get_prompt_checks():
        return seeded_rows()

    failures = {"content_safety": prompt_checks_module.UNHEALTHY_AFTER_FAILURES}
    monkeypatch.setattr(admin_router, "get_prompt_checks", get_prompt_checks)
    monkeypatch.setattr(
        admin_router, "get_consecutive_failures", lambda kind: failures.get(kind, 0)
    )

    items = asyncio.run(admin_router.list_prompt_checks())

    assert [(item.kind, item.healthy) for item in items] == [
        ("content_safety", False),
        ("pii", True),
    ]
    assert (
        items[0].consecutive_failures == prompt_checks_module.UNHEALTHY_AFTER_FAILURES
    )
    assert items[1].consecutive_failures == 0


def test_missing_failure_key_counts_as_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    class Client:
        def get(self, key):
            return None

    monkeypatch.setattr(prompt_checks_module, "get_redis_client", lambda: Client())

    assert prompt_checks_module.get_consecutive_failures("pii") == 0


def test_unreachable_redis_counts_as_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom():
        raise RuntimeError("no redis")

    monkeypatch.setattr(prompt_checks_module, "get_redis_client", boom)

    assert prompt_checks_module.get_consecutive_failures("pii") == 0


def patch_check(kind: str, body: PromptCheckPatch):
    class CurrentUser:
        id = ADMIN_ID

    return asyncio.run(admin_router.patch_prompt_check(kind, body, CurrentUser()))


def test_patching_a_mode(db: FakeSession, invalidations: list[str]) -> None:
    result = patch_check("content_safety", PromptCheckPatch(mode="block"))

    assert result.kind == "content_safety"
    assert result.mode == "block"
    assert result.updated_by == ADMIN_ID
    assert db.rows[0].mode == "block"
    assert db.rows[1].mode == "log"


def test_patching_thresholds_replaces_them(
    db: FakeSession, invalidations: list[str]
) -> None:
    result = patch_check("pii", PromptCheckPatch(thresholds={"pii": 0.8}))

    assert result.thresholds == {"pii": 0.8}
    assert db.rows[1].thresholds == {"pii": 0.8}


def test_unset_fields_are_left_alone(db: FakeSession, invalidations: list[str]) -> None:
    patch_check("content_safety", PromptCheckPatch(mode="warn"))

    assert db.rows[0].thresholds == DEFAULT_THRESHOLDS["content_safety"]
    assert db.rows[0].model == DEFAULT_MODEL


def test_unknown_kind_is_rejected(db: FakeSession, invalidations: list[str]) -> None:
    with pytest.raises(HTTPException) as raised:
        patch_check("astrology", PromptCheckPatch(mode="block"))

    assert raised.value.status_code == 404
    assert not db.committed
    assert invalidations == []


def test_health_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError, match="can never block"):
        PromptCheckPatch(thresholds={"health": 0.5})


def test_write_invalidates_the_cache(db: FakeSession, invalidations: list[str]) -> None:
    patch_check("pii", PromptCheckPatch(mode="block"))

    assert invalidations == [prompt_checks_module.REDIS_PROMPT_CHECKS_KEY]
    assert db.committed
