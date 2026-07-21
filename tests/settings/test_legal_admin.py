import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
        "button_label": "Continuer",
    }
    arena.update(arena_overrides)
    return {
        "arena": arena,
        "sign_in": {
            "checkbox_label": "Libellé de connexion configuré",
        },
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


def test_immediate_publication_retires_active_terms():
    active = LegalDocument(
        kind="terms",
        version="1.0",
        language="fr",
        content="Previous terms",
        content_hash=legal.legal_document_hash("Previous terms"),
        effective_at=datetime.now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    with patch.object(legal, "get_session", session_factory(fake_session)):
        published = asyncio.run(
            legal.publish_terms(
                version="2.0",
                language="fr",
                content="New terms",
                effective_at=None,
            )
        )

    assert fake_session.committed
    assert active.retired_at == published.effective_at
    assert published.content_hash == legal.legal_document_hash("New terms")
    assert published.content == "New terms"
    assert published in fake_session.added


def test_scheduled_publication_keeps_current_terms_active():
    fake_session = FakeSession([[]])
    with patch.object(legal, "get_session", session_factory(fake_session)):
        published = asyncio.run(
            legal.publish_terms(
                version="3.0",
                language="fr-FR",
                content="Scheduled terms",
                effective_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
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
        effective_at=datetime.now() - timedelta(days=1),
    )
    fake_session = FakeSession([[], [active]])
    with patch.object(legal, "get_session", session_factory(fake_session)):
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
    assert_raises(
        ValidationError,
        lambda: PublishPrivacyPolicyBody.model_validate(
            {
                "version": "2.0",
                "locale": "fr",
                "content": "Nouvelle politique",
                "confirm_publication": False,
            }
        ),
    )


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
    with patch.object(legal, "get_session", session_factory(fake_session)):
        assert_raises(
            legal.DuplicateLegalDocumentError,
            lambda: asyncio.run(
                legal.publish_terms(
                    version="2.0",
                    language="fr",
                    content="Changed",
                    effective_at=None,
                )
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


def test_admin_publication_requires_explicit_confirmation():
    assert_raises(
        ValidationError,
        lambda: PublishTermsBody.model_validate(
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
        lambda: PublishTermsBody.model_validate(
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


if __name__ == "__main__":
    test_immediate_publication_retires_active_terms()
    test_scheduled_publication_keeps_current_terms_active()
    test_immediate_privacy_policy_publication_retires_only_previous_policy()
    test_privacy_policy_publication_requires_explicit_confirmation()
    test_published_version_cannot_be_reused_with_different_content()
    test_effective_date_must_stay_in_publication_window()
    test_admin_publication_requires_explicit_confirmation()
    test_admin_publication_rejects_invalid_locale()
    test_mutable_presentation_comes_from_app_settings()
    test_presentation_uses_defaults_when_not_configured()
