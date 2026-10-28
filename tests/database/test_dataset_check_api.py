import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

import backend.admin.dataset_check as api
import backend.arena.checks as checks
from utils.database import dataset_checks
from utils.database.models.dataset_check import (
    DEFAULT_CRITERIA,
    DatasetCheck,
    DatasetCheckUpsert,
)

ADMIN = SimpleNamespace(id=uuid.UUID("11111111-2222-3333-4444-555555555555"))
REAL_CLIENT = httpx.AsyncClient


class FakeSession:
    def __init__(self, row: DatasetCheck | None):
        self.row = row

    async def get(self, model, key):
        return self.row

    def add(self, row):
        self.row = row

    async def commit(self):
        pass

    async def refresh(self, row):
        pass


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    session = FakeSession(
        DatasetCheck(
            id=1,
            model="test/decider",
            api_key="stored-key",
            criteria=[dict(c) for c in DEFAULT_CRITERIA],
            updated_at=datetime(2026, 1, 1),
        )
    )

    @asynccontextmanager
    async def get_session():
        yield session

    async def app_settings():
        return SimpleNamespace(default_locale="fr", enabled_locales=["fr", "en"])

    monkeypatch.setattr(dataset_checks, "get_session", get_session)
    monkeypatch.setattr(api, "get_app_settings", app_settings)
    return session


@pytest.fixture
def decider(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Every question scores 0.4, except the English one."""
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        answers = {
            key: {"noul": 0.9 if key == "language_en" else 0.4}
            for key in body["questions"]
        }
        return httpx.Response(200, json={"answers": answers})

    monkeypatch.setattr(
        checks.httpx,
        "AsyncClient",
        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )

    def no_redis():
        raise ConnectionError("no redis in tests")

    monkeypatch.setattr(checks, "get_redis_client", no_redis)
    return requests


def put(body: dict):
    return asyncio.run(api.put_dataset_check(DatasetCheckUpsert(**body), ADMIN))


def test_reading_never_returns_the_key(db):
    public = asyncio.run(api.read_dataset_check())
    assert public.has_api_key
    assert "stored-key" not in public.model_dump_json()
    assert [c.key for c in public.criteria] == ["pii", "spam"]


def test_a_blank_key_keeps_the_stored_one(db):
    put({"model": "other/decider", "api_key": "  ", "criteria": DEFAULT_CRITERIA})
    assert db.row.api_key == "stored-key"
    assert db.row.model == "other/decider"
    assert db.row.updated_by == ADMIN.id


def test_removing_the_key_falls_back_to_the_prompt_check(db, monkeypatch):
    async def prompt_check():
        return SimpleNamespace(api_key="arena-key")

    monkeypatch.setattr(dataset_checks, "get_prompt_check", prompt_check)
    public = asyncio.run(api.delete_dataset_check_api_key(ADMIN))
    assert not public.has_api_key
    assert not public.no_api_key
    assert asyncio.run(dataset_checks.dataset_check_api_key(db.row)) == "arena-key"


def test_a_criterion_cannot_take_a_fixed_key():
    criteria = [dict(DEFAULT_CRITERIA[0], key="language_fr")]
    with pytest.raises(ValidationError):
        DatasetCheckUpsert(criteria=criteria)


def test_trying_uses_the_unsaved_settings_and_writes_nothing(db, decider):
    before = db.row.model_dump()
    result = asyncio.run(
        api.try_dataset_check(
            api.DatasetCheckTryBody(text="[user]: hello", category_threshold=0.3)
        )
    )
    assert db.row.model_dump() == before
    # Seeded criteria exclude at 0.3, so 0.4 keeps it out.
    assert not result.published
    assert result.excluded_by == ["pii", "spam"]
    assert len(result.categories) == 17
    assert result.languages == ["en"]
    assert decider[0]["model"] == "test/decider"

    looser = [dict(c, threshold=0.5) for c in DEFAULT_CRITERIA]
    result = asyncio.run(
        api.try_dataset_check(
            api.DatasetCheckTryBody(text="[user]: hello", criteria=looser)
        )
    )
    assert result.published and result.excluded_by == []
    assert result.categories == ["Other"]


def test_trying_without_a_model_says_so(db, decider):
    db.row.model = ""
    result = asyncio.run(api.try_dataset_check(api.DatasetCheckTryBody(text="hi")))
    assert result.message == api.NO_MODEL_MESSAGE
    assert decider == []
