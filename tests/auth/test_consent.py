import asyncio
import contextlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import utils.database.models  # noqa: E402,F401
from backend.auth import router as auth_router  # noqa: E402
from backend.auth import services as auth_services  # noqa: E402
from backend.auth.services import _create_session  # noqa: E402
from backend.settings import legal as legal_settings  # noqa: E402
from backend.settings import router as settings_router  # noqa: E402
from backend.settings.legal import (  # noqa: E402
    fallback_legal_presentation,
    legal_document_public_hash,
)
from utils.database.models.auth import (  # noqa: E402
    AnonymousConsentLog,
    AuthSession,
    ConsentLog,
    LegalDocument,
    User,
)


def evidence(**overrides):
    value = {
        "terms_version": "2.0",
        "terms_hash": "a" * 64,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "locale": "fr",
        "legal_information_acknowledged": True,
    }
    value.update(overrides)
    return value


def test_authentication_contract_is_separate_from_consent():
    body = auth_router.EmailVerifyBody.model_validate(
        {"email": "user@example.com", "code": "123456"}
    )
    assert body.email == "user@example.com"
    assert "consent" not in type(body).model_fields


def test_public_config_exposes_the_deployment_url(monkeypatch):
    async def fake_get_app_settings():
        return SimpleNamespace(
            auth_access_policy="anonymous_first",
            auth_domain_allowlist=[],
            platform_name="Example arena",
            logo=None,
        )

    monkeypatch.setattr(auth_router, "get_app_settings", fake_get_app_settings)
    monkeypatch.setattr(
        auth_router.settings, "COMPARIA_APP_URL", "https://arena.example.test"
    )

    config = asyncio.run(auth_router.get_config())

    assert config.platform_url == "https://arena.example.test"


def test_legal_information_acknowledgement_cannot_be_false():
    try:
        auth_router.ConsentAssertion.model_validate(
            evidence(legal_information_acknowledged=False)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A false mandatory acknowledgement was accepted")


def test_research_reuse_is_not_modelled_as_optional_consent():
    try:
        auth_router.ConsentAssertion.model_validate(
            evidence(research_data_sharing=False)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("The removed optional research field was accepted")

    paths = {route.path for route in auth_router.router.routes}
    assert "/auth/consent/research/withdraw" not in paths
    assert "/auth/consent/anonymous/research/withdraw" not in paths


def test_changed_terms_are_rejected_before_authentication():
    original = auth_router.validate_active_terms

    async def stale(*_args):
        return None

    auth_router.validate_active_terms = stale
    try:
        app = FastAPI()
        app.include_router(auth_router.router)
        client = TestClient(app)
        response = client.post(
            "/auth/consent/anonymous",
            json={
                "consent": evidence(),
            },
            cookies={"anonymous_session": "anonymous-test-token"},
        )
        assert response.status_code == 409
    finally:
        auth_router.validate_active_terms = original


def test_email_code_requires_current_anonymous_acceptance():
    original_captcha = auth_router.verify_altcha_token
    original_acceptance = auth_router.has_current_terms_acceptance
    auth_router.verify_altcha_token = lambda _payload: (True, None)

    async def missing_acceptance(**_kwargs):
        return False

    auth_router.has_current_terms_acceptance = missing_acceptance
    try:
        app = FastAPI()
        app.include_router(auth_router.router)
        client = TestClient(app)
        client.cookies.set("anonymous_session", "anonymous-test-token")
        response = client.post(
            "/auth/email/request",
            json={"email": "user@example.com", "altcha_payload": "valid"},
        )
        assert response.status_code == 428
    finally:
        auth_router.verify_altcha_token = original_captcha
        auth_router.has_current_terms_acceptance = original_acceptance


def test_public_terms_response_is_privacy_minimal():
    original = settings_router.get_active_terms
    original_presentation = settings_router.get_legal_presentation
    document = LegalDocument(
        kind="terms",
        version="2.0",
        language="fr",
        content="Document public",
        content_hash="a" * 64,
        effective_at=datetime.now(),
    )

    async def active(_locale):
        return document

    async def configured_presentation():
        return fallback_legal_presentation()

    settings_router.get_active_terms = active
    settings_router.get_legal_presentation = configured_presentation
    try:
        app = FastAPI()
        app.include_router(settings_router.router)
        response = TestClient(app).get("/settings/legal/terms?locale=fr")
        assert response.status_code == 200
        assert set(response.json()) == {
            "version",
            "content_hash",
            "locale",
            "content",
            "published_at",
            "effective_at",
            "presentation",
        }
    finally:
        settings_router.get_active_terms = original
        settings_router.get_legal_presentation = original_presentation


def test_current_acceptance_returns_the_document_version():
    document = LegalDocument(
        kind="terms",
        version="2026.07",
        language="fr",
        content="Published terms",
        content_hash="a" * 64,
        effective_at=datetime.now(),
    )

    async def active_terms(_language):
        return document

    anonymous_hash = "b" * 64
    public_hash = legal_document_public_hash(document)
    original_active_terms = legal_settings.get_active_terms
    original_database_uri = auth_services.settings.COMPARIA_DB_URI
    original_acceptance = auth_services._DEV_ANONYMOUS_CONSENTS.get(anonymous_hash)
    legal_settings.get_active_terms = active_terms
    auth_services.settings.COMPARIA_DB_URI = None
    auth_services._DEV_ANONYMOUS_CONSENTS[anonymous_hash] = {
        "terms": {
            "version": document.version,
            "content_hash": public_hash,
            "locale": document.language,
        }
    }
    try:
        version = asyncio.run(
            auth_services.get_current_terms_acceptance_version(
                user_id=None, anonymous_user_hash=anonymous_hash
            )
        )
    finally:
        legal_settings.get_active_terms = original_active_terms
        auth_services.settings.COMPARIA_DB_URI = original_database_uri
        if original_acceptance is None:
            auth_services._DEV_ANONYMOUS_CONSENTS.pop(anonymous_hash, None)
        else:
            auth_services._DEV_ANONYMOUS_CONSENTS[anonymous_hash] = original_acceptance

    assert version == document.version


def test_authentication_session_does_not_infer_consent():
    class FakeSession:
        def __init__(self):
            self.added = []

        def add(self, value):
            self.added.append(value)

    session = FakeSession()
    user = User(email="user@example.com")
    asyncio.run(_create_session(session, user, "127.0.0.1", None, None))
    assert (
        len([value for value in session.added if isinstance(value, AuthSession)]) == 1
    )
    assert not [value for value in session.added if isinstance(value, ConsentLog)]


def test_authentication_session_does_not_merge_anonymous_comparisons():
    class EmptyResult:
        def first(self):
            return None

    class FakeSession:
        def __init__(self):
            self.added = []
            self.executed = []

        def add(self, value):
            self.added.append(value)

        async def exec(self, _statement):
            return EmptyResult()

        async def execute(self, statement):
            self.executed.append(statement)

    session = FakeSession()
    user = User(email="user@example.com")

    asyncio.run(
        _create_session(
            session,
            user,
            "127.0.0.1",
            None,
            None,
            anonymous_user_hash="b" * 64,
        )
    )

    assert (
        len([value for value in session.added if isinstance(value, AuthSession)]) == 1
    )
    assert session.executed == []


def test_explicit_acceptance_records_one_required_purpose():
    class FakeSession:
        def __init__(self):
            self.added = []

        def add(self, value):
            self.added.append(value)

        async def commit(self):
            pass

    session = FakeSession()

    @contextlib.asynccontextmanager
    async def fake_get_session():
        yield session

    document = LegalDocument(
        kind="terms",
        version="2.0",
        language="fr",
        content="Document public",
        content_hash="a" * 64,
        effective_at=datetime.now(),
    )
    assertion = auth_router.ConsentAssertion.model_validate(evidence())
    original = auth_services.get_session
    original_db_uri = auth_services.settings.COMPARIA_DB_URI
    auth_services.get_session = fake_get_session
    auth_services.settings.COMPARIA_DB_URI = "postgresql://test/test"
    try:
        asyncio.run(
            auth_services.record_user_consent(
                User(email="user@example.com").id,
                assertion,
                document,
                None,
            )
        )
    finally:
        auth_services.get_session = original
        auth_services.settings.COMPARIA_DB_URI = original_db_uri

    logs = [value for value in session.added if isinstance(value, ConsentLog)]
    assert [log.purpose for log in logs] == ["terms_and_participation"]
    assert logs[0].document_hash == legal_document_public_hash(document)


def test_anonymous_proof_is_linked_without_changing_acceptance_time():
    accepted_at = datetime(2026, 7, 20, 10, 0, 0)
    document = LegalDocument(
        kind="terms",
        version="2.0",
        language="fr",
        content="Document public",
        content_hash="a" * 64,
        effective_at=datetime.now(),
    )
    anonymous = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=document.id,
        terms_version=document.version,
        document_hash=document.content_hash,
        language="fr",
        purpose="terms_and_participation",
        client_accepted_at=accepted_at,
        consented_at=accepted_at,
    )
    user = User(email="user@example.com")
    auth_session = AuthSession(
        user_id=user.id,
        token_hash="c" * 64,
        expires_at=datetime(2026, 8, 20),
        ip="not-collected",
    )

    class Result:
        def __init__(self, value):
            self.value = value

        def first(self):
            return self.value

    class FakeSession:
        def __init__(self):
            self.results = [Result(anonymous), Result(None)]
            self.added = []

        async def exec(self, _statement):
            return self.results.pop(0)

        def add(self, value):
            self.added.append(value)

    session = FakeSession()
    asyncio.run(
        auth_services._associate_anonymous_acceptance(
            session, user, auth_session, anonymous.anonymous_user_hash
        )
    )
    linked = next(value for value in session.added if isinstance(value, ConsentLog))
    assert linked.user_id == user.id
    assert linked.auth_session_id == auth_session.id
    assert linked.source_anonymous_consent_id == anonymous.id
    assert linked.consented_at == accepted_at
    assert linked.document_hash == anonymous.document_hash


if __name__ == "__main__":
    test_authentication_contract_is_separate_from_consent()
    test_legal_information_acknowledgement_cannot_be_false()
    test_research_reuse_is_not_modelled_as_optional_consent()
    test_changed_terms_are_rejected_before_authentication()
    test_email_code_requires_current_anonymous_acceptance()
    test_public_terms_response_is_privacy_minimal()
    test_current_acceptance_returns_the_document_version()
    test_authentication_session_does_not_infer_consent()
    test_authentication_session_does_not_merge_anonymous_comparisons()
    test_explicit_acceptance_records_one_required_purpose()
    test_anonymous_proof_is_linked_without_changing_acceptance_time()
