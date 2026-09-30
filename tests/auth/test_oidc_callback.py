"""
Tests for the OIDC callback (no DB, no Redis, no real identity provider).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_callback.py
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.oidc import PendingLogin  # noqa: E402
from tests.auth.fake_oidc_provider import (  # noqa: E402
    CLIENT_ID,
    CLIENT_SECRET,
    ENCRYPTED_CLIENT_SECRET,
    ISSUER,
    FakeProvider,
    serving,
)
from utils.database.models.auth import (  # noqa: E402
    AuthSession,
    TotpChallenge,
    User,
)


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


def _settings_row(**overrides):
    fields = dict(
        auth_access_policy="anonymous_first",
        auth_domain_allowlist=[],
        auth_methods=["email_code", "oidc"],
        oidc_issuer=ISSUER,
        oidc_client_id=CLIENT_ID,
        oidc_client_secret_encrypted=ENCRYPTED_CLIENT_SECRET,
        oidc_scopes=["openid", "email"],
        oidc_button_label="Se connecter avec ProConnect",
        oidc_button_logo=b"png-bytes",
        oidc_button_logo_content_type="image/png",
        platform_name="Test",
        primary_color_light="#000091",
        primary_color_dark="#8585F6",
        secondary_color_light="#6A6AF4",
        secondary_color_dark="#CACAFB",
        homepage_url=None,
        logo=None,
        logo_version=None,
        enabled_locales=["fr"],
        default_locale="fr",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


USER_ID = uuid.uuid4()


@contextlib.contextmanager
def routed(
    row=None,
    pending=None,
    provider=None,
    login=None,
    state_cookie="good-state",
):
    if row is None:
        row = _settings_row()
    if provider is None:
        provider = FakeProvider()
    if pending is None:
        pending = PendingLogin(nonce="the-nonce", redirect="/", merge=False)

    async def get_app_settings():
        return row

    def consume_state(state):
        # Tests reuse a single in-flight state; the router only calls this
        # once per request, so returning the pending login is enough.
        return pending if state == "good-state" else None

    # Spy: records whether the happy-path `login_with_oidc` service ran. Failure
    # paths must never reach it (no User row, no session minted).
    login_calls = []

    if login is None:

        async def login_with_oidc(**kwargs):
            login_calls.append(kwargs)
            return auth_services.LoginResult("session", "session-token"), USER_ID

    else:
        login_with_oidc = login

    merge_calls = []

    async def merge_anonymous_comparisons(user_id, anonymous_user_hash):
        merge_calls.append((user_id, anonymous_user_hash))

    with (
        serving(provider),
        patched(
            auth_router,
            get_app_settings=get_app_settings,
            consume_state=consume_state,
            login_with_oidc=login_with_oidc,
            merge_anonymous_comparisons=merge_anonymous_comparisons,
        ),
    ):
        app = FastAPI()
        app.include_router(auth_router.router)
        client = TestClient(app)
        client.cookies.set("anonymous_session", "token")
        if state_cookie:
            # What `oidc_login` handed this browser when it started the flow.
            client.cookies.set("oidc_state", state_cookie)
        # Expose the spies without changing the `routed() as client` convention.
        client._login_calls = login_calls  # type: ignore[attr-defined]
        client._merge_calls = merge_calls  # type: ignore[attr-defined]
        client._provider = provider  # type: ignore[attr-defined]
        yield client


def _provider(*, id_token=None, userinfo=None):
    """The default fake provider with some claims changed."""
    provider = FakeProvider()
    provider.id_token_claims.update(id_token or {})
    provider.userinfo_claims.update(userinfo or {})
    return provider


def _login_redirect(response):
    """A failure-path response: 302 to /login?error=..., no session cookie."""
    assert response.status_code == 302, response.text
    from urllib.parse import parse_qs, urlsplit

    parsed = urlsplit(response.headers["location"])
    # Absolute: the frontend is a separate origin from this backend route.
    assert parsed.geturl().startswith(auth_router.settings.COMPARIA_APP_URL)
    assert parsed.path == "/login"
    reason = parse_qs(parsed.query).get("error", [None])[0]
    assert reason, f"expected an error param, got {response.headers['location']!r}"
    # No session is ever minted on a failure path.
    assert "auth_session" not in response.headers.get("set-cookie", "")
    return reason


def test_callback_signs_in_and_sets_the_session_cookie_on_success():
    with routed() as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == f"{auth_router.settings.COMPARIA_APP_URL}/"
    set_cookie = response.headers["set-cookie"]
    assert "auth_session=session-token" in set_cookie
    assert "httponly" in set_cookie.lower()


def test_callback_rejects_a_missing_state():
    with routed() as client:
        response = client.get(
            "/auth/oidc/callback", params={"code": "auth-code"}, follow_redirects=False
        )
    reason = _login_redirect(response)
    assert reason == "invalid_state"
    assert not client._login_calls


def test_callback_rejects_an_unknown_state():
    with routed() as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "never-issued"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "invalid_state"
    assert not client._login_calls


def test_callback_rejects_a_missing_code():
    with routed() as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "missing_code"
    assert not client._login_calls


def test_callback_rejects_a_nonce_mismatch():
    provider = _provider(id_token={"nonce": "different-nonce"})
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "invalid_nonce"
    assert not client._login_calls


def test_callback_rejects_when_provider_returns_no_email():
    with routed(provider=_provider(userinfo={"email": None})) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "no_email"
    assert not client._login_calls


def test_callback_rejects_an_unverified_email():
    """A provider that hands back `email_verified: false` is asserting it did
    *not* check ownership of the address — trusting it would let an attacker
    claim any email (including a pre-seeded admin's) and take over that
    account by matching on email."""

    provider = _provider(
        userinfo={"email": "boss@example.com", "email_verified": False}
    )
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "email_not_verified"
    assert not client._login_calls


def test_callback_allows_a_missing_email_verified_claim():
    """`email_verified` is optional in the OIDC spec, and some real providers
    never send it — ProConnect's documented userinfo claims don't include it.
    An absent claim must not lock out every login from
    those providers; only an explicit `false` is rejected."""

    provider = _provider()
    del provider.userinfo_claims["email_verified"]
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert response.headers["location"] == f"{auth_router.settings.COMPARIA_APP_URL}/"
    assert client._login_calls


def test_callback_denies_an_email_outside_the_domain_allowlist():
    row = _settings_row(auth_domain_allowlist=["allowed.example.test"])
    with routed(row=row) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "domain_not_allowed"
    assert not client._login_calls


def test_callback_rejects_when_oidc_disabled_in_methods():
    row = _settings_row(auth_methods=["email_code"])
    with routed(row=row) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "oidc_unavailable"
    assert not client._login_calls


def test_callback_redirects_when_discovery_is_missing_required_endpoints():
    provider = FakeProvider()
    provider.discovery = {"issuer": ISSUER}
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "provider_error"
    assert not client._login_calls


def test_callback_redirects_when_discovery_raises():
    provider = FakeProvider()
    provider.unreachable = True
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "provider_error"
    assert not client._login_calls


def test_callback_redirects_when_provider_returns_an_error_param():
    """The IdP redirects back with `error` when the user denies consent or the
    provider rejects the request — there is no code to exchange."""
    with routed() as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"error": "access_denied", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "provider_error"
    assert not client._login_calls


def test_callback_redirects_when_the_token_endpoint_rejects_the_code():
    """A denied/expired/reused code makes the token endpoint reject the
    exchange; the round trip is unrecoverable from the browser."""

    provider = FakeProvider()
    provider.token_status = 400
    with routed(provider=provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "provider_error"
    assert not client._login_calls


def test_callback_failure_leaves_no_session_cookie_on_any_path():
    """Every failure path is a redirect to /login with no auth_session cookie
    set — verified collectively here, in addition to the per-path checks."""
    rows = [
        ("missing_state", {}, {}),
        ("unknown_state", {}, {"state": "never-issued"}),
        ("provider_error_param", {}, {"error": "access_denied"}),
        (
            "no_email",
            {"provider": _provider(userinfo={"email": None})},
            {"code": "x", "state": "good-state"},
        ),
        (
            "email_not_verified",
            {"provider": _provider(userinfo={"email_verified": False})},
            {"code": "x", "state": "good-state"},
        ),
        (
            "domain_not_allowed",
            {"row": _settings_row(auth_domain_allowlist=["x.test"])},
            {"code": "x", "state": "good-state"},
        ),
    ]
    for _label, kwargs, params in rows:
        with routed(**kwargs) as client:
            response = client.get(
                "/auth/oidc/callback", params=params, follow_redirects=False
            )
        _login_redirect(response)
        assert not client._login_calls


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    """Records added objects and replays canned results for `login_with_oidc`."""

    def __init__(self, results):
        self.results = list(results)
        self.added = []
        self.committed = False

    async def exec(self, _statement):
        return _FakeResult(self.results.pop(0) if self.results else [])

    async def execute(self, _statement):
        pass

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True


@contextlib.contextmanager
def fake_session(session):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    with patched(auth_services, get_session=get_session):
        yield session


def test_oidc_login_creates_a_user_when_none_exists():
    session = FakeSession(results=[[]])
    with fake_session(session):
        token = asyncio.run(
            auth_services.login_with_oidc(
                email="newcomer@example.com",
                ip="127.0.0.1",
                user_agent=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert session.committed
    assert any(isinstance(obj, User) for obj in session.added)
    created = next(obj for obj in session.added if isinstance(obj, User))
    assert created.email == "newcomer@example.com"
    assert created.role == "user"


def test_oidc_login_reuses_an_existing_account_instead_of_duplicating_it():
    existing = User(email="agent@example.com")
    session = FakeSession(results=[[existing]])
    with fake_session(session):
        token = asyncio.run(
            auth_services.login_with_oidc(
                email="agent@example.com",
                ip="127.0.0.1",
                user_agent=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert session.committed
    assert not any(isinstance(obj, User) for obj in session.added)


def test_oidc_login_lands_on_a_pre_seeded_admin_account():
    admin = User(email="boss@example.com", role="admin")
    session = FakeSession(results=[[admin]])
    with fake_session(session):
        token = asyncio.run(
            auth_services.login_with_oidc(
                email="boss@example.com",
                ip="127.0.0.1",
                user_agent=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert admin.role == "admin"
    assert not any(isinstance(obj, User) for obj in session.added)


def test_callback_reuses_an_existing_account_instead_of_duplicating_it():
    """Router-seam test: an existing email-code account is reused when the
    same email authenticates via OIDC. Wires the real
    `login_with_oidc` service to a FakeSession that already holds a User row for
    the callback's email, then asserts the callback succeeds and adds no
    new User to the session."""
    existing = User(email="agent@example.com")
    session = FakeSession(results=[[existing]])

    async def login(**kwargs):
        return await auth_services.login_with_oidc(**kwargs)

    with fake_session(session):
        with routed(login=login) as client:
            response = client.get(
                "/auth/oidc/callback",
                params={"code": "auth-code", "state": "good-state"},
                follow_redirects=False,
            )

    assert response.status_code == 302
    assert response.headers["location"] == f"{auth_router.settings.COMPARIA_APP_URL}/"
    assert "auth_session=" in response.headers["set-cookie"]
    assert not any(isinstance(obj, User) for obj in session.added)


def _callback(client, **params):
    params = {"code": "auth-code", "state": "good-state", **params}
    return client.get("/auth/oidc/callback", params=params, follow_redirects=False)


def test_callback_rejects_a_state_this_browser_never_asked_for():
    """Login CSRF: an attacker starts a sign-in with their own provider
    account, stops before the callback and has a victim open it. The state is
    valid in Redis, but the victim's browser never received it."""
    with routed(state_cookie=None) as client:
        response = _callback(client)
    assert _login_redirect(response) == "invalid_state"
    assert not client._login_calls


def test_callback_rejects_a_state_cookie_from_another_sign_in():
    with routed(state_cookie="some-other-state") as client:
        response = _callback(client)
    assert _login_redirect(response) == "invalid_state"
    assert not client._login_calls


def test_callback_spends_the_state_cookie_on_success_and_failure():
    with routed() as client:
        succeeded = _callback(client)
    with routed() as client:
        failed = _callback(client, state="never-issued")

    for response in (succeeded, failed):
        cookies = response.headers.get_list("set-cookie")
        spent = [c for c in cookies if c.startswith("oidc_state=")]
        assert spent, cookies
        assert "max-age=0" in spent[0].lower()


def test_callback_lands_on_the_page_the_sign_in_started_from():
    pending = PendingLogin(nonce="the-nonce", redirect="/arena?x=1", merge=False)
    with routed(pending=pending) as client:
        response = _callback(client)
    assert response.status_code == 302
    assert (
        response.headers["location"]
        == f"{auth_router.settings.COMPARIA_APP_URL}/arena?x=1"
    )


def test_callback_never_redirects_off_site():
    pending = PendingLogin(nonce="the-nonce", redirect="//evil.test", merge=False)
    with routed(pending=pending) as client:
        response = _callback(client)
    assert response.headers["location"] == f"{auth_router.settings.COMPARIA_APP_URL}/"


def test_callback_merges_anonymous_comparisons_when_asked():
    pending = PendingLogin(nonce="the-nonce", redirect="/", merge=True)
    with routed(pending=pending) as client:
        response = _callback(client)
    assert response.status_code == 302
    assert client._merge_calls == [(USER_ID, auth_router._hash("token"))]


def test_callback_does_not_merge_unless_asked():
    with routed() as client:
        _callback(client)
    assert client._merge_calls == []


def test_callback_lowercases_the_email_like_the_email_flow():
    with routed(provider=_provider(userinfo={"email": "Agent@Example.COM"})) as client:
        _callback(client)
    assert client._login_calls[0]["email"] == "agent@example.com"


def test_callback_rejects_a_malformed_email_claim():
    with routed(provider=_provider(userinfo={"email": "not-an-address"})) as client:
        response = _callback(client)
    assert _login_redirect(response) == "no_email"
    assert not client._login_calls


def test_callback_reports_a_deactivated_account():
    async def login(**_kwargs):
        return None

    with routed(login=login) as client:
        response = _callback(client)
    assert _login_redirect(response) == "account_unavailable"


def test_callback_redirects_when_the_client_secret_cannot_be_decrypted():
    row = _settings_row(oidc_client_secret_encrypted=b"not-a-fernet-token")
    with routed(row=row) as client:
        response = _callback(client)
    assert _login_redirect(response) == "oidc_unavailable"
    assert not client._login_calls


def test_callback_sends_the_configured_client_and_the_code_to_the_token_endpoint():
    with routed() as client:
        _callback(client)
    (token_request,) = client._provider.requests_to("/token")
    form = parse_qs(token_request.content.decode())
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["auth-code"]
    assert form["client_id"] == [CLIENT_ID]
    assert form["client_secret"] == [CLIENT_SECRET]
    assert form["redirect_uri"] == [auth_router.oidc_callback_url()]


def test_callback_rejects_an_id_token_issued_by_another_provider():
    provider = _provider(id_token={"iss": "https://elsewhere.test"})
    with routed(provider=provider) as client:
        response = _callback(client)
    assert _login_redirect(response) == "provider_error"
    assert not client._login_calls


def test_callback_reads_a_userinfo_answered_as_a_jwt():
    """ProConnect signs its userinfo response: it comes back as
    `application/jwt`, not JSON."""
    provider = _provider(userinfo={"email": "Signed@Example.com"})
    provider.userinfo_as_jwt = True
    with routed(provider=provider) as client:
        response = _callback(client)
    assert response.status_code == 302
    assert client._login_calls[0]["email"] == "signed@example.com"


def test_callback_redirects_when_the_token_response_has_no_access_token():
    provider = FakeProvider()
    provider.token_body = {"id_token": "whatever", "token_type": "Bearer"}
    with routed(provider=provider) as client:
        response = _callback(client)
    assert _login_redirect(response) == "provider_error"
    assert not client._login_calls


def test_callback_rejects_an_id_token_without_a_nonce():
    provider = _provider()
    del provider.id_token_claims["nonce"]
    with routed(provider=provider) as client:
        response = _callback(client)
    assert _login_redirect(response) == "invalid_nonce"
    assert not client._login_calls


def test_oidc_login_owes_the_second_factor_of_an_admin_with_an_authenticator():
    """The provider stands in for the email code, not for the authenticator:
    an enrolled admin gets a challenge, never a session, like in the email
    flow."""
    admin = User(email="boss@example.com", role="admin")
    confirmed_totp = uuid.uuid4()
    session = FakeSession(results=[[admin], [confirmed_totp]])
    with fake_session(session):
        login, user_id = asyncio.run(
            auth_services.login_with_oidc(
                email="boss@example.com",
                ip="127.0.0.1",
                user_agent=None,
                anonymous_user_hash=None,
            )
        )

    assert login.kind == "totp_challenge"
    assert user_id == admin.id
    assert any(isinstance(obj, TotpChallenge) for obj in session.added)
    assert not any(isinstance(obj, AuthSession) for obj in session.added)


def test_callback_hands_an_enrolled_admin_to_the_authenticator_step():
    async def login(**_kwargs):
        return auth_services.LoginResult("totp_challenge", "challenge-token"), USER_ID

    pending = PendingLogin(nonce="the-nonce", redirect="/admin", merge=True)
    with routed(pending=pending, login=login) as client:
        response = _callback(client)

    assert response.status_code == 302
    assert response.headers["location"] == (
        f"{auth_router.settings.COMPARIA_APP_URL}/login?step=totp&redirect=%2Fadmin"
    )
    cookies = response.headers.get_list("set-cookie")
    assert any(c.startswith("auth_totp_challenge=challenge-token") for c in cookies)
    assert not any(c.startswith("auth_session=challenge-token") for c in cookies)
    # A session left open for another account does not survive either.
    assert any(c.startswith('auth_session=""') for c in cookies)
    # Nothing lands in an account the visitor has not fully signed in to.
    assert client._merge_calls == []


def test_oidc_login_refuses_a_deactivated_account():
    deleted = User(email="gone@example.com", deleted_at=datetime.now())
    session = FakeSession(results=[[deleted]])
    with fake_session(session):
        signed_in = asyncio.run(
            auth_services.login_with_oidc(
                email="gone@example.com",
                ip="127.0.0.1",
                user_agent=None,
                anonymous_user_hash=None,
            )
        )

    assert signed_in is None
    assert not session.committed


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
