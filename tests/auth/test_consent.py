"""
Unit tests for the consent flow (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/auth/test_consent.py
"""

import asyncio
import contextlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from utils.database.models.auth import (  # noqa: E402
    AnonymousConsentLog,
    AuthSession,
    ConsentLog,
    LegalDocument,
    User,
)
from utils.database.models.comparison import (  # noqa: E402
    LEGACY_PARTICIPATION_TERMS_VERSION,
)
from utils.database.models.utils import utc_now  # noqa: E402

DOCUMENT = LegalDocument(
    kind="terms",
    version="2026.07",
    language="fr",
    content="Conditions publiées",
    content_hash="a" * 64,
    effective_at=datetime(2026, 7, 1),
)


def evidence(**overrides):
    value = {
        "terms_version": DOCUMENT.version,
        "terms_hash": DOCUMENT.content_hash,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "locale": DOCUMENT.language,
        "legal_information_acknowledged": True,
    }
    value.update(overrides)
    return value


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, *results):
        self.results = list(results)
        self.added = []
        self.executed = []
        self.committed = False

    async def exec(self, _statement):
        return FakeResult(self.results.pop(0) if self.results else [])

    async def execute(self, statement):
        self.executed.append(statement)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True


@contextlib.contextmanager
def fake_session(session):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    original = auth_services.get_session
    auth_services.get_session = get_session
    try:
        yield session
    finally:
        auth_services.get_session = original


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


@contextlib.contextmanager
def active_terms(document):
    async def get_active_legal_document(_kind, _language):
        return document

    with patched(auth_services, get_active_legal_document=get_active_legal_document):
        with patched(auth_router, get_active_legal_document=get_active_legal_document):
            yield


class FakeRedis:
    def incr(self, key):
        return 1

    def expire(self, key, ttl):
        pass

    def get(self, key):
        return None

    def delete(self, key):
        pass


@contextlib.contextmanager
def routed(**overrides):
    """Serve the router with the plumbing every login route needs stubbed out."""

    async def app_settings():
        return SimpleNamespace(auth_domain_allowlist=[])

    async def signup_questions_answered(**_kwargs):
        # These tests are about the consent gate. An instance with no signup
        # questions is the default, and that is what this stands in for.
        return True

    async def account_exists(_email):
        # A first-time visitor, which is the case the gates are written for.
        return False

    overrides.setdefault("signup_questions_answered", signup_questions_answered)
    overrides.setdefault("account_exists", account_exists)

    with patched(
        auth_router,
        get_redis_client=lambda: FakeRedis(),
        verify_altcha_token=lambda _payload: (True, None),
        get_app_settings=app_settings,
        **overrides,
    ):
        app = FastAPI()
        app.include_router(auth_router.router)
        test_client = TestClient(app)
        test_client.cookies.set("anonymous_session", "token")
        yield test_client


def test_acknowledgement_cannot_be_declined():
    try:
        auth_router.ConsentAssertion.model_validate(
            evidence(legal_information_acknowledged=False)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("a declined acknowledgement was accepted")


def test_acceptance_time_must_be_zoned_and_recent():
    for accepted_at in (
        datetime.now().isoformat(),
        (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    ):
        try:
            auth_router.ConsentAssertion.model_validate(
                evidence(accepted_at=accepted_at)
            )
        except ValueError:
            continue
        raise AssertionError(f"an unusable acceptance time was accepted: {accepted_at}")


def test_acceptance_time_is_normalised_to_naive_utc():
    accepted_at = datetime.now(timezone(timedelta(hours=2)))
    assertion = auth_router.ConsentAssertion.model_validate(
        evidence(accepted_at=accepted_at.isoformat())
    )
    assert assertion.accepted_at.tzinfo is None
    assert assertion.accepted_at == accepted_at.astimezone(timezone.utc).replace(
        tzinfo=None
    )


def test_recorded_times_agree_with_the_browser_acceptance():
    """Guards against consented_at being written in the host's local time."""
    accepted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session = FakeSession()
    with fake_session(session):
        asyncio.run(
            auth_services.record_user_consent(
                User(email="a@b.fr").id, DOCUMENT, accepted_at, None
            )
        )

    log = next(value for value in session.added if isinstance(value, ConsentLog))
    assert abs(log.consented_at - log.client_accepted_at) < timedelta(seconds=5)
    assert log.document_hash == DOCUMENT.content_hash
    assert log.purpose == "terms_and_participation"


def test_an_aware_acceptance_time_is_stored_on_the_utc_now_scale():
    """The router normalises, but a backfill or a second endpoint may not."""
    session = FakeSession()
    with fake_session(session):
        asyncio.run(
            auth_services.record_anonymous_consent(
                "b" * 64, DOCUMENT, datetime.now(timezone(timedelta(hours=3)))
            )
        )

    log = next(
        value for value in session.added if isinstance(value, AnonymousConsentLog)
    )
    assert log.client_accepted_at.tzinfo is None
    assert abs(log.client_accepted_at - utc_now()) < timedelta(seconds=5)


def test_anonymous_acceptance_records_the_document_it_saw():
    session = FakeSession()
    accepted_at = datetime(2026, 7, 27, 8, 0, 0)
    with fake_session(session):
        asyncio.run(
            auth_services.record_anonymous_consent("b" * 64, DOCUMENT, accepted_at)
        )

    log = next(
        value for value in session.added if isinstance(value, AnonymousConsentLog)
    )
    assert log.document_id == DOCUMENT.id
    assert log.terms_version == DOCUMENT.version
    assert log.language == DOCUMENT.language
    assert log.client_accepted_at == accepted_at


def test_signing_in_is_not_an_acceptance():
    session = FakeSession()
    asyncio.run(
        auth_services._create_session(
            session, User(email="a@b.fr"), "10.0.0.1", None, None
        )
    )

    assert len([v for v in session.added if isinstance(v, AuthSession)]) == 1
    assert not [v for v in session.added if isinstance(v, ConsentLog)]


def test_anonymous_acceptance_is_carried_over_at_its_original_time():
    accepted_at = datetime(2026, 7, 20, 10, 0, 0)
    acceptance = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=DOCUMENT.id,
        terms_version=DOCUMENT.version,
        document_hash=DOCUMENT.content_hash,
        language="fr",
        client_accepted_at=accepted_at,
        consented_at=accepted_at,
    )
    user = User(email="a@b.fr")
    auth_session = AuthSession(
        user_id=user.id,
        token_hash="c" * 64,
        expires_at=datetime(2026, 8, 20),
        ip="10.0.0.1",
    )
    session = FakeSession([acceptance], [])

    asyncio.run(
        auth_services._associate_anonymous_acceptance(
            session, user, auth_session, acceptance.anonymous_user_hash
        )
    )

    linked = next(value for value in session.added if isinstance(value, ConsentLog))
    assert linked.source_anonymous_consent_id == acceptance.id
    assert linked.auth_session_id == auth_session.id
    assert linked.consented_at == accepted_at
    assert linked.associated_at is not None


def test_an_already_linked_acceptance_is_not_copied_twice():
    acceptance = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=DOCUMENT.id,
        terms_version=DOCUMENT.version,
        document_hash=DOCUMENT.content_hash,
        language="fr",
        client_accepted_at=datetime(2026, 7, 20),
    )
    user = User(email="a@b.fr")
    session = FakeSession(
        [acceptance], [ConsentLog(user_id=user.id, terms_version="x", ip="")]
    )

    asyncio.run(
        auth_services._associate_anonymous_acceptance(
            session,
            user,
            AuthSession(
                user_id=user.id,
                token_hash="c" * 64,
                expires_at=datetime(2026, 8, 20),
                ip="10.0.0.1",
            ),
            acceptance.anonymous_user_hash,
        )
    )

    assert not session.added


def test_acceptance_of_a_superseded_document_is_rejected():
    with active_terms(None), fake_session(FakeSession()), routed() as test_client:
        response = test_client.post(
            "/auth/consent/anonymous", json={"consent": evidence()}
        )
    assert response.status_code == 409


def test_acceptance_of_the_active_document_is_recorded():
    session = FakeSession()
    with active_terms(DOCUMENT), fake_session(session), routed() as test_client:
        response = test_client.post(
            "/auth/consent/anonymous", json={"consent": evidence()}
        )
    assert response.status_code == 204
    assert session.committed


def test_current_acceptance_reports_the_document_version():
    acceptance = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=DOCUMENT.id,
        terms_version=DOCUMENT.version,
        document_hash=DOCUMENT.content_hash,
        language="fr",
        client_accepted_at=datetime(2026, 7, 20),
    )
    with active_terms(DOCUMENT), fake_session(FakeSession([acceptance])):
        version = asyncio.run(
            auth_services.get_current_terms_acceptance_version(
                user_id=None, anonymous_user_hash="b" * 64
            )
        )
    assert version == DOCUMENT.version


def test_acceptance_of_a_retired_document_no_longer_counts():
    superseded = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=LegalDocument(
            kind="terms",
            version="2026.06",
            language="fr",
            content="Anciennes conditions",
            content_hash="d" * 64,
            effective_at=datetime(2026, 6, 1),
        ).id,
        terms_version="2026.06",
        document_hash="d" * 64,
        language="fr",
        client_accepted_at=datetime(2026, 6, 20),
    )
    with active_terms(DOCUMENT), fake_session(FakeSession([superseded])):
        version = asyncio.run(
            auth_services.get_current_terms_acceptance_version(
                user_id=None, anonymous_user_hash="b" * 64
            )
        )
    assert version is None


def test_participation_stays_open_when_nothing_is_published():
    """Otherwise nobody, not even an admin, could sign in to publish the terms."""
    with active_terms(None), fake_session(FakeSession()):
        version = asyncio.run(
            auth_services.get_current_terms_acceptance_version(
                user_id=None, anonymous_user_hash="b" * 64
            )
        )
    assert version == LEGACY_PARTICIPATION_TERMS_VERSION


def test_login_code_requires_a_current_acceptance():
    async def declined(**_kwargs):
        return False

    with routed(has_current_terms_acceptance=declined) as test_client:
        response = test_client.post(
            "/auth/email/request", json={"email": "a@b.fr", "altcha_payload": "valid"}
        )
    assert response.status_code == 428


def test_login_code_requires_the_signup_questions():
    """
    The gate is enforced here, not only in the sign-in form. On an arena whose
    point is a verified professional audience, a check the browser makes alone
    is no check: the answers would come to mean 'professionals, plus everyone
    who posted straight to the API', which is not a column anyone can analyse.
    """

    async def unanswered(**_kwargs):
        return False

    async def granted(**_kwargs):
        return True

    with routed(
        signup_questions_answered=unanswered, has_current_terms_acceptance=granted
    ) as test_client:
        response = test_client.post(
            "/auth/email/request", json={"email": "a@b.fr", "altcha_payload": "valid"}
        )
    assert response.status_code == 428


def test_signup_questions_do_not_gate_an_account_that_already_exists():
    """
    The questions gate the creation of an account, not the return of someone
    who already has one. An admin adding a question must not lock existing
    users out of the profile page that is the only place they could answer it.
    """

    async def unanswered(**_kwargs):
        raise AssertionError("the gate ran for an account that already exists")

    async def granted(**_kwargs):
        return True

    async def known_account(_email):
        return True

    with routed(
        signup_questions_answered=unanswered,
        has_current_terms_acceptance=granted,
        account_exists=known_account,
    ) as test_client:
        response = test_client.post(
            "/auth/email/request", json={"email": "a@b.fr", "altcha_payload": "valid"}
        )
    assert response.status_code == 204


def test_invite_acceptance_requires_a_current_acceptance():
    async def declined(**_kwargs):
        return False

    async def accept_invite(**_kwargs):
        raise AssertionError("the invite was spent before the terms were checked")

    with routed(
        has_current_terms_acceptance=declined, accept_invite=accept_invite
    ) as test_client:
        response = test_client.post("/auth/invite/accept", json={"token": "invite"})

    assert response.status_code == 428


def test_an_accepted_invite_carries_the_acceptance_of_the_visitor():
    """The box ticked on the invite page has to follow them onto the account."""
    accepted = {}

    async def granted(**_kwargs):
        return True

    async def accept_invite(**kwargs):
        accepted.update(kwargs)
        return "session-token"

    with routed(
        has_current_terms_acceptance=granted, accept_invite=accept_invite
    ) as test_client:
        response = test_client.post("/auth/invite/accept", json={"token": "invite"})

    assert response.status_code == 200
    assert accepted["anonymous_user_hash"] == auth_services._hash("token")


def test_the_carried_over_acceptance_answers_for_the_first_message():
    """Otherwise the arena gate would ask again right after the invite."""
    acceptance = AnonymousConsentLog(
        anonymous_user_hash="b" * 64,
        document_id=DOCUMENT.id,
        terms_version=DOCUMENT.version,
        document_hash=DOCUMENT.content_hash,
        language="fr",
        client_accepted_at=datetime(2026, 7, 20, 10, 0, 0),
    )
    user = User(email="a@b.fr")
    carried = ConsentLog(
        user_id=user.id,
        source_anonymous_consent_id=acceptance.id,
        document_id=acceptance.document_id,
        terms_version=acceptance.terms_version,
        document_hash=acceptance.document_hash,
        language=acceptance.language,
        client_accepted_at=acceptance.client_accepted_at,
        ip="not_collected",
    )

    with active_terms(DOCUMENT), fake_session(FakeSession([carried])):
        version = asyncio.run(
            auth_services.get_current_terms_acceptance_version(
                user_id=user.id, anonymous_user_hash="b" * 64
            )
        )

    assert version == DOCUMENT.version


def test_login_code_is_not_blocked_when_nothing_is_published():
    """Otherwise the admin who has to publish the terms cannot sign in either."""
    sent = []

    async def request_login_code(_email):
        return "123456"

    async def send_login_code(email, _code):
        sent.append(email)

    with (
        active_terms(None),
        fake_session(FakeSession()),
        routed(
            request_login_code=request_login_code, send_login_code=send_login_code
        ) as test_client,
    ):
        response = test_client.post(
            "/auth/email/request", json={"email": "a@b.fr", "altcha_payload": "valid"}
        )

    assert response.status_code == 204
    assert sent == ["a@b.fr"]


if __name__ == "__main__":
    for name, test in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            test()
