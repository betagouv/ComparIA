"""Focused tests for immutable terms publication and admin contracts."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.admin.router import (  # noqa: E402
    PublishPrivacyPolicyBody,
    PublishTermsBody,
)
from backend.settings import legal  # noqa: E402
from utils.database.models.auth import LegalDocument  # noqa: E402


def presentation_payload(**arena_overrides):
    arena = {
        "title": "Titre configuré",
        "introduction": "Introduction configurée",
        "checkbox_label": "Libellé obligatoire configuré",
        "links": [
            {"label": "Conditions", "href": "/arene/modalites"},
            {
                "label": "Données personnelles",
                "href": "/arene/donnees-personnelles",
            },
        ],
        "button_label": "Continuer",
    }
    arena.update(arena_overrides)
    return {
        "arena": arena,
        "sign_in": {
            "checkbox_label": "Libellé de connexion configuré",
            "links": [{"label": "Conditions", "href": "/arene/modalites"}],
        },
    }


def presentation(**arena_overrides):
    return legal.LegalPresentation.model_validate(
        presentation_payload(**arena_overrides)
    )


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


def test_immediate_publication_retires_active_terms(monkeypatch):
    active = LegalDocument(
        kind="terms",
        version="1.0",
        language="fr",
        content="Previous terms",
        content_hash=legal.legal_document_hash("Previous terms"),
        effective_at=datetime.now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    monkeypatch.setattr(legal, "get_session", session_factory(fake_session))

    published = asyncio.run(
        legal.publish_terms(
            version="2.0",
            language="fr",
            content="New terms",
            presentation=presentation(),
            effective_at=None,
        )
    )

    assert fake_session.committed
    assert active.retired_at == published.effective_at
    assert published.content_hash == legal.legal_document_public_hash(published)
    assert legal.decode_legal_document(published.content).content == "New terms"
    assert published in fake_session.added


def test_scheduled_publication_keeps_current_terms_active(monkeypatch):
    fake_session = FakeSession([[]])
    monkeypatch.setattr(legal, "get_session", session_factory(fake_session))

    published = asyncio.run(
        legal.publish_terms(
            version="3.0",
            language="fr-FR",
            content="Scheduled terms",
            presentation=presentation(),
            effective_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )

    assert published.retired_at is None
    assert fake_session.committed


def test_immediate_privacy_policy_publication_retires_only_previous_policy(monkeypatch):
    active = LegalDocument(
        kind="privacy_policy",
        version="1.0",
        language="fr",
        content="Previous privacy policy",
        content_hash=legal.legal_document_hash("Previous privacy policy"),
        effective_at=datetime.now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    monkeypatch.setattr(legal, "get_session", session_factory(fake_session))

    published = asyncio.run(
        legal.publish_privacy_policy(
            version="2.0",
            language="fr",
            content="# Nouvelle politique",
            effective_at=None,
        )
    )

    assert fake_session.committed
    assert active.retired_at == published.effective_at
    assert published.kind == "privacy_policy"
    assert published.content == "# Nouvelle politique"
    assert published.content_hash == legal.legal_document_hash(published.content)


def test_privacy_policy_publication_requires_explicit_confirmation():
    with pytest.raises(ValidationError):
        PublishPrivacyPolicyBody.model_validate(
            {
                "version": "2.0",
                "locale": "fr",
                "content": "Nouvelle politique",
                "confirm_publication": False,
            }
        )


def test_published_version_cannot_be_reused_with_different_content(monkeypatch):
    existing = LegalDocument(
        kind="terms",
        version="2.0",
        language="fr",
        content="Original",
        content_hash=legal.legal_document_hash("Original"),
        effective_at=datetime(2026, 8, 1, 12, 0),
    )
    fake_session = FakeSession([[existing]])
    monkeypatch.setattr(legal, "get_session", session_factory(fake_session))

    with pytest.raises(legal.DuplicateLegalDocumentError):
        asyncio.run(
            legal.publish_terms(
                version="2.0",
                language="fr",
                content="Changed",
                presentation=presentation(),
                effective_at=None,
            )
        )

    assert not fake_session.committed


@pytest.mark.parametrize(
    "value",
    [
        datetime.now(timezone.utc) - timedelta(minutes=6),
        datetime.now(timezone.utc) + timedelta(days=366),
    ],
)
def test_effective_date_must_stay_in_publication_window(value):
    with pytest.raises(legal.InvalidEffectiveDateError):
        legal.normalize_effective_at(value)


def test_admin_publication_requires_explicit_confirmation():
    with pytest.raises(ValidationError):
        PublishTermsBody.model_validate(
            {
                "version": "2.0",
                "locale": "fr",
                "content": "New terms",
                "presentation": presentation_payload(),
                "confirm_publication": False,
            }
        )


def test_admin_publication_rejects_invalid_locale():
    with pytest.raises(ValidationError):
        PublishTermsBody.model_validate(
            {
                "version": "2.0",
                "locale": "not a locale",
                "content": "New terms",
                "presentation": presentation_payload(),
                "confirm_publication": True,
            }
        )


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "//evil.example/modalites",
        "https://evil.example/modalites",
        "https://cnil.fr/page?tracking=yes",
        "/arene/route-inconnue",
    ],
)
def test_presentation_rejects_unsafe_or_unapproved_links(href):
    payload = presentation_payload()
    payload["arena"]["links"][0]["href"] = href
    with pytest.raises(ValidationError):
        legal.LegalPresentation.model_validate(payload)


@pytest.mark.parametrize(
    "href",
    [
        "/terms",
        "/arene/modalites",
        "/arene/donnees-personnelles#droits",
        "https://www.cnil.fr/fr/comprendre-le-rgpd",
    ],
)
def test_presentation_accepts_internal_and_allowlisted_links(href):
    payload = presentation_payload()
    payload["arena"]["links"][0]["href"] = href
    assert legal.LegalPresentation.model_validate(payload).arena.links[0].href == href


def test_legacy_document_gets_canonical_presentation_hash(monkeypatch):
    document = LegalDocument(
        kind="terms",
        version="legacy",
        language="fr",
        content="Legacy terms",
        content_hash=legal.legal_document_hash("Legacy terms"),
        effective_at=datetime.now(),
    )
    public_hash = legal.legal_document_public_hash(document)
    assert public_hash != document.content_hash
    assert legal.decode_legal_document(document.content).content == "Legacy terms"

    async def active(_language):
        return document

    monkeypatch.setattr(legal, "get_active_terms", active)
    assert (
        asyncio.run(legal.validate_active_terms("legacy", public_hash, "fr"))
        == document
    )


def test_new_envelope_hash_covers_copy_and_presentation():
    first = legal.legal_document_envelope("Published terms", presentation())
    second = legal.legal_document_envelope(
        "Published terms", presentation(title="Autre titre")
    )
    serialized = legal.serialize_legal_document(first)

    assert legal.decode_legal_document(serialized) == first
    assert legal.legal_envelope_hash(first) != legal.legal_envelope_hash(second)


def test_mutable_presentation_overrides_terms_snapshot(monkeypatch):
    configured = presentation_payload(title="Parcours modifiable")

    async def app_settings():
        return SimpleNamespace(legal_presentation=configured)

    monkeypatch.setattr(legal, "get_app_settings", app_settings)

    result = asyncio.run(legal.get_legal_presentation())

    assert result.arena.title == "Parcours modifiable"


def test_presentation_falls_back_to_terms_snapshot(monkeypatch):
    document = LegalDocument(
        kind="terms",
        version="1.0",
        language="fr",
        content=legal.serialize_legal_document(
            legal.legal_document_envelope(
                "Terms", presentation(title="Parcours publié")
            )
        ),
        content_hash="a" * 64,
        effective_at=datetime.now(),
    )

    async def app_settings():
        return SimpleNamespace(legal_presentation=None)

    monkeypatch.setattr(legal, "get_app_settings", app_settings)

    result = asyncio.run(legal.get_legal_presentation(document))

    assert result.arena.title == "Parcours publié"
