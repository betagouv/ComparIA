import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.admin.suggestions as admin_suggestions
import backend.suggestions.router as suggestions_router
from backend.admin.router import router as admin_router
from backend.auth.dependencies import require_admin
from backend.suggestions.services import (
    SuggestionAlreadyExistsError,
    SuggestionCategoryAlreadyExistsError,
    SuggestionNotFoundError,
)
from utils.database.models.suggestion import (
    AdminSuggestion,
    AdminSuggestionCategory,
    PublicSuggestion,
    PublicSuggestionCategory,
    PublicSuggestionsResponse,
)


def _category() -> AdminSuggestionCategory:
    return AdminSuggestionCategory(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        locale="fr",
        key="administrative",
        title="Administratif",
        description="Rédiger un document administratif",
        icon="i-ri-draft-line",
        display_order=0,
    )


def _suggestion() -> AdminSuggestion:
    return AdminSuggestion(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        text="Écris une lettre.",
        locale="fr",
        category_id=_category().id,
        category_title="Administratif",
        status="available",
        created_at=datetime(2026, 7, 27),
        updated_at=datetime(2026, 7, 27),
    )


def test_public_suggestions_returns_grouped_categories(monkeypatch):
    async def fake_list(locale):
        assert locale == "fr"
        return PublicSuggestionsResponse(
            categories=[
                PublicSuggestionCategory(
                    id=_category().id,
                    key="administrative",
                    title="Administratif",
                    description="Rédiger un document administratif",
                    icon="i-ri-draft-line",
                    suggestions=[
                        PublicSuggestion(id=_suggestion().id, text="Écris une lettre.")
                    ],
                )
            ]
        )

    monkeypatch.setattr(suggestions_router, "list_public_suggestions", fake_list)
    app = FastAPI()
    app.include_router(suggestions_router.router)

    response = TestClient(app).get("/suggestions?locale=fr")

    assert response.status_code == 200
    assert response.json()["categories"][0]["suggestions"] == [
        {"id": str(_suggestion().id), "text": "Écris une lettre."}
    ]


def test_admin_suggestions_requires_an_admin():
    app = FastAPI()
    app.include_router(admin_router)

    response = TestClient(app).get("/admin/suggestions")

    assert response.status_code == 401


def test_admin_suggestions_passes_filters_and_returns_categories(monkeypatch):
    received = {}

    async def fake_list(**kwargs):
        received.update(kwargs)
        return [_suggestion()], 1, [_category()]

    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    monkeypatch.setattr(admin_suggestions, "list_admin_suggestions", fake_list)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).get(
        f"/admin/suggestions?search=lettre&status=available&locale=fr&category_id={_category().id}&page=2&page_size=20"
    )

    assert response.status_code == 200
    assert received == {
        "search": "lettre",
        "status": "available",
        "locale": "fr",
        "category_id": _category().id,
        "page": 2,
        "page_size": 20,
    }
    assert response.json()["total"] == 1
    assert response.json()["categories"][0]["key"] == "administrative"


def test_create_suggestion_rejects_blank_text_before_service(monkeypatch):
    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions",
        json={"category_id": str(_category().id), "text": "   "},
    )

    assert response.status_code == 422


def test_create_suggestion_normalizes_text_and_passes_admin(monkeypatch):
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    received = {}

    async def fake_admin():
        return SimpleNamespace(id=admin_id)

    async def fake_create(body, *, created_by):
        received.update(body=body, created_by=created_by)
        return _suggestion()

    monkeypatch.setattr(admin_suggestions, "create_suggestion", fake_create)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions",
        json={"category_id": str(_category().id), "text": "  Écris une lettre.  "},
    )

    assert response.status_code == 201
    assert received["body"].text == "Écris une lettre."
    assert received["created_by"] == admin_id


def test_create_suggestion_returns_conflict_for_duplicate(monkeypatch):
    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    async def fake_create(*args, **kwargs):
        raise SuggestionAlreadyExistsError()

    monkeypatch.setattr(admin_suggestions, "create_suggestion", fake_create)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions",
        json={"category_id": str(_category().id), "text": "Écris une lettre."},
    )

    assert response.status_code == 409


def test_create_category_validates_remix_icon():
    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions/categories",
        json={
            "locale": "fr",
            "title": "Sciences",
            "description": "Comprendre les sciences",
            "icon": "custom-science-icon",
        },
    )

    assert response.status_code == 422


def test_create_category_normalizes_fields(monkeypatch):
    received = {}

    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    async def fake_create(body):
        received["body"] = body
        return _category().model_copy(
            update={
                "key": "sciences",
                "title": body.title,
                "description": body.description,
                "icon": body.icon,
                "tooltip": body.tooltip,
            }
        )

    monkeypatch.setattr(admin_suggestions, "create_suggestion_category", fake_create)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions/categories",
        json={
            "locale": "fr",
            "title": "  Sciences  ",
            "description": "  Comprendre les sciences  ",
            "icon": "  i-ri-flask-line  ",
            "tooltip": "  Exemples pédagogiques  ",
        },
    )

    assert response.status_code == 201
    assert received["body"].title == "Sciences"
    assert received["body"].description == "Comprendre les sciences"
    assert received["body"].icon == "i-ri-flask-line"
    assert received["body"].tooltip == "Exemples pédagogiques"


def test_create_category_returns_conflict_for_duplicate(monkeypatch):
    async def fake_admin():
        return SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000003"))

    async def fake_create(*args, **kwargs):
        raise SuggestionCategoryAlreadyExistsError()

    monkeypatch.setattr(admin_suggestions, "create_suggestion_category", fake_create)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).post(
        "/admin/suggestions/categories",
        json={
            "locale": "fr",
            "title": "Administratif",
            "description": "Rédiger un document administratif",
            "icon": "i-ri-draft-line",
        },
    )

    assert response.status_code == 409


def test_archive_suggestion_passes_admin_and_handles_missing_suggestion(monkeypatch):
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    received = {}

    async def fake_admin():
        return SimpleNamespace(id=admin_id)

    async def fake_archive(suggestion_id, *, archived, updated_by):
        received.update(
            suggestion_id=suggestion_id,
            archived=archived,
            updated_by=updated_by,
        )
        return _suggestion().model_copy(update={"status": "archived"})

    monkeypatch.setattr(admin_suggestions, "set_suggestion_archived", fake_archive)
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[require_admin] = fake_admin

    response = TestClient(app).patch(
        f"/admin/suggestions/{_suggestion().id}",
        json={"archived": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert received == {
        "suggestion_id": _suggestion().id,
        "archived": True,
        "updated_by": admin_id,
    }

    async def fake_missing(*args, **kwargs):
        raise SuggestionNotFoundError()

    monkeypatch.setattr(admin_suggestions, "set_suggestion_archived", fake_missing)
    response = TestClient(app).patch(
        f"/admin/suggestions/{_suggestion().id}",
        json={"archived": False},
    )
    assert response.status_code == 404
