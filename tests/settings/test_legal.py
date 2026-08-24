"""
Unit tests for legal document publication and the public endpoints (no DB).

Run with pytest, or directly:
    uv run python tests/settings/test_legal.py
"""

import asyncio
import importlib.util
import json
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.settings.router as settings_router  # noqa: E402
from backend.admin.router import (  # noqa: E402
    PublishLegalDocumentBody,
    _to_admin_legal_document,
)
from backend.settings import legal  # noqa: E402
from utils.database.models.auth import LegalDocument  # noqa: E402
from utils.database.models.utils import utc_now  # noqa: E402


def presentation_payload(**arena_overrides):
    arena = {
        "title": "Titre configuré",
        "introduction": "Introduction configurée",
        "checkbox_label": "Libellé obligatoire configuré",
        "button_label": "Continuer",
    }
    arena.update(arena_overrides)
    return {
        "arena": arena,
        "sign_in": {"checkbox_label": "Libellé de connexion configuré"},
    }


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, results):
        self.results = iter(results)
        self.added = []
        self.committed = False

    async def exec(self, _statement):
        return FakeResult(next(self.results))

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass

    async def refresh(self, _value):
        pass


def session_factory(fake_session):
    @asynccontextmanager
    async def factory():
        yield fake_session

    return factory


def assert_raises(error_type, action):
    try:
        action()
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def publish(fake_session, **kwargs):
    with patch.object(legal, "get_session", session_factory(fake_session)):
        return asyncio.run(legal.publish_legal_document(**kwargs))


def test_seeded_terms_version_matches_the_migration():
    """The migration keeps its own literal so it never depends on app code."""
    path = (
        Path(__file__).resolve().parents[2]
        / "utils/database/alembic/versions"
        / "e4a8c2d9f1b7_add_versioned_legal_documents.py"
    )
    spec = importlib.util.spec_from_file_location("legal_documents_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.SEED_VERSION == legal.SEEDED_TERMS_VERSION


def test_immediate_publication_retires_active_terms():
    active = LegalDocument(
        kind="terms",
        version="1.0",
        language="fr",
        content="Previous terms",
        content_hash=legal.legal_document_hash("Previous terms"),
        effective_at=utc_now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    published = publish(
        fake_session,
        kind="terms",
        version="2.0",
        language="fr",
        content="New terms",
        effective_at=None,
    )

    assert fake_session.committed
    assert active.retired_at == published.effective_at
    assert published.content_hash == legal.legal_document_hash("New terms")
    assert published in fake_session.added


def test_published_and_effective_timestamps_are_both_utc():
    """Guards against mixing local time and UTC in the same row."""
    published = publish(
        FakeSession([[], []]),
        kind="terms",
        version="2.0",
        language="fr",
        content="New terms",
        effective_at=None,
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(published.effective_at - published.published_at) < timedelta(seconds=5)
    assert abs(now - published.published_at) < timedelta(seconds=5)


def test_scheduled_publication_keeps_current_terms_active():
    fake_session = FakeSession([[]])
    published = publish(
        fake_session,
        kind="terms",
        version="3.0",
        language="fr-FR",
        content="Scheduled terms",
        effective_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert published.retired_at is None
    assert fake_session.committed


def test_immediate_privacy_policy_publication_retires_only_previous_policy():
    active = LegalDocument(
        kind="privacy_policy",
        version="1.0",
        language="fr",
        content="Previous privacy policy",
        content_hash=legal.legal_document_hash("Previous privacy policy"),
        effective_at=utc_now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    published = publish(
        fake_session,
        kind="privacy_policy",
        version="2.0",
        language="fr",
        content="# Nouvelle politique",
        effective_at=None,
    )

    assert fake_session.committed
    assert active.retired_at == published.effective_at
    assert published.kind == "privacy_policy"
    assert published.content_hash == legal.legal_document_hash(published.content)


def test_published_version_cannot_be_reused_with_different_content():
    existing = LegalDocument(
        kind="terms",
        version="2.0",
        language="fr",
        content="Original",
        content_hash=legal.legal_document_hash("Original"),
        effective_at=datetime(2026, 8, 1, 12, 0),
    )
    fake_session = FakeSession([[existing]])
    assert_raises(
        legal.DuplicateLegalDocumentError,
        lambda: publish(
            fake_session,
            kind="terms",
            version="2.0",
            language="fr",
            content="Changed",
            effective_at=None,
        ),
    )

    assert not fake_session.committed


def test_effective_date_must_stay_in_publication_window():
    for value in (
        datetime.now(timezone.utc) - timedelta(minutes=6),
        datetime.now(timezone.utc) + timedelta(days=366),
    ):
        assert_raises(
            legal.InvalidEffectiveDateError,
            lambda value=value: legal.normalize_effective_at(value),
        )


def test_aware_effective_date_is_stored_as_utc():
    paris = timezone(timedelta(hours=2))
    value = datetime.now(paris) + timedelta(days=1)
    assert legal.normalize_effective_at(value) == value.astimezone(
        timezone.utc
    ).replace(tzinfo=None)


def test_admin_publication_requires_explicit_confirmation():
    assert_raises(
        ValidationError,
        lambda: PublishLegalDocumentBody.model_validate(
            {
                "version": "2.0",
                "locale": "fr",
                "content": "New terms",
                "confirm_publication": False,
            }
        ),
    )


def test_admin_publication_rejects_invalid_locale():
    assert_raises(
        ValidationError,
        lambda: PublishLegalDocumentBody.model_validate(
            {
                "version": "2.0",
                "locale": "not a locale",
                "content": "New terms",
                "confirm_publication": True,
            }
        ),
    )


def test_mutable_presentation_comes_from_app_settings():
    configured = presentation_payload(title="Parcours modifiable")

    async def app_settings():
        return SimpleNamespace(legal_presentation=configured)

    with patch.object(legal, "get_app_settings", app_settings):
        result = asyncio.run(legal.get_legal_presentation())

    assert result.arena.title == "Parcours modifiable"


def test_presentation_uses_defaults_when_not_configured():
    async def app_settings():
        return SimpleNamespace(legal_presentation=None)

    with patch.object(legal, "get_app_settings", app_settings):
        result = asyncio.run(legal.get_legal_presentation())

    assert result == legal.fallback_legal_presentation()


def terms_document(**overrides) -> LegalDocument:
    fields = {
        "kind": "terms",
        "version": "1.0",
        "language": "fr",
        "content": "Conditions",
        "content_hash": legal.legal_document_hash("Conditions"),
        "effective_at": utc_now(),
    }
    fields.update(overrides)
    return LegalDocument(**fields)


@contextmanager
def public_client(presentation=None, document=None):
    document = document or terms_document()

    async def active_document(_kind, _language):
        return document

    async def get_presentation():
        return presentation or legal.fallback_legal_presentation()

    app = FastAPI()
    app.include_router(settings_router.router)
    with (
        patch.object(settings_router, "get_active_legal_document", active_document),
        patch.object(settings_router, "get_legal_presentation", get_presentation),
    ):
        yield TestClient(app)


def test_public_terms_are_revalidated_with_an_etag():
    with public_client() as client:
        first = client.get("/api/settings/legal/terms")
        assert first.status_code == 200
        assert first.headers["Cache-Control"] == "no-cache"

        etag = first.headers["ETag"]
        cached = client.get("/api/settings/legal/terms", headers={"If-None-Match": etag})
        assert cached.status_code == 304


def test_public_terms_etag_changes_with_the_presentation():
    with public_client() as client:
        etag = client.get("/api/settings/legal/terms").headers["ETag"]

    edited = legal.LegalPresentation.model_validate(
        presentation_payload(title="Titre modifié")
    )
    with public_client(edited) as client:
        assert client.get("/api/settings/legal/terms").headers["ETag"] != etag


def test_public_timestamps_carry_a_utc_offset():
    """Without the marker a browser reads the value as local time.

    The skew is the size of the host offset, so a document taking effect just
    after midnight would be shown as the previous day.
    """
    stored = datetime(2026, 7, 27, 22, 30)
    with public_client(document=terms_document(effective_at=stored)) as client:
        payload = client.get("/api/settings/legal/terms").json()

    for key in ("published_at", "effective_at"):
        assert datetime.fromisoformat(payload[key]).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(payload["effective_at"]) == stored.replace(
        tzinfo=timezone.utc
    )


def test_admin_timestamps_carry_a_utc_offset():
    stored = datetime(2026, 7, 27, 22, 30)
    document = terms_document(effective_at=stored, retired_at=stored)
    payload = json.loads(_to_admin_legal_document(document).model_dump_json())

    for key in ("published_at", "effective_at", "retired_at"):
        assert datetime.fromisoformat(payload[key]).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(payload["retired_at"]) == stored.replace(
        tzinfo=timezone.utc
    )


if __name__ == "__main__":
    for name, case in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            case()
            print(f"ok {name}")
