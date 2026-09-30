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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.oidc import PendingLogin  # noqa: E402
from utils.database.models.auth import User  # noqa: E402


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
        oidc_issuer="https://idp.example.test",
        oidc_client_id="client-123",
        oidc_client_secret_encrypted=b"encrypted",
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
        enabled_locales=["fr"],
        default_locale="fr",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _discovery():
    return {
        "issuer": "https://idp.example.test",
        "authorization_endpoint": "https://idp.example.test/authorize",
        "token_endpoint": "https://idp.example.test/token",
        "userinfo_endpoint": "https://idp.example.test/userinfo",
    }


USER_ID = uuid.uuid4()


@contextlib.contextmanager
def routed(
    row=None,
    pending=None,
    exchange=None,
    discover=None,
    oidc_login=None,
    decrypt=None,
    state_cookie="good-state",
):
    if row is None:
        row = _settings_row()
    if pending is None:
        pending = PendingLogin(nonce="the-nonce", redirect="/", merge=False)

    async def get_app_settings():
        return row

    def consume_state(state):
        # Tests reuse a single in-flight state; the router only calls this
        # once per request, so returning the pending login is enough.
        return pending if state == "good-state" else None

    if discover is None:

        async def discover_provider(_issuer):
            return _discovery()

    else:
        discover_provider = discover

    if exchange is None:

        async def exchange_code_for_claims(**_kwargs):
            return {
                "email": "agent@example.com",
                "email_verified": True,
                "nonce": "the-nonce",
            }

    else:
        exchange_code_for_claims = exchange

    # Spy: records whether the happy-path `oidc_login` service ran. Failure
    # paths must never reach it (no User row, no session minted).
    login_calls = []

    if oidc_login is None:

        async def oidc_login_service(**kwargs):
            login_calls.append(kwargs)
            return "session-token", USER_ID

    else:
        oidc_login_service = oidc_login

    merge_calls = []

    async def merge_anonymous_comparisons(user_id, anonymous_user_hash):
        merge_calls.append((user_id, anonymous_user_hash))

    if decrypt is None:

        def decrypt_oidc_secret(_ciphertext):
            return "super-secret"

    else:
        decrypt_oidc_secret = decrypt

    with patched(
        auth_router,
        get_app_settings=get_app_settings,
        consume_state=consume_state,
        discover_provider=discover_provider,
        exchange_code_for_claims=exchange_code_for_claims,
        oidc_login_service=oidc_login_service,
        decrypt_oidc_secret=decrypt_oidc_secret,
        merge_anonymous_comparisons=merge_anonymous_comparisons,
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
        yield client


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
    async def exchange_code_for_claims(**_kwargs):
        return {"email": "agent@example.com", "nonce": "different-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "invalid_nonce"
    assert not client._login_calls


def test_callback_rejects_when_provider_returns_no_email():
    async def exchange_code_for_claims(**_kwargs):
        return {"email": None, "email_verified": True, "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
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

    async def exchange_code_for_claims(**_kwargs):
        return {
            "email": "boss@example.com",
            "email_verified": False,
            "nonce": "the-nonce",
        }

    with routed(exchange=exchange_code_for_claims) as client:
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

    async def exchange_code_for_claims(**_kwargs):
        return {"email": "agent@example.com", "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
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
    async def discover_provider(_issuer):
        return {"issuer": "https://idp.example.test"}

    with routed(discover=discover_provider) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "provider_error"
    assert not client._login_calls


def test_callback_redirects_when_discovery_raises():
    async def discover_provider(_issuer):
        raise RuntimeError("network down")

    with routed(discover=discover_provider) as client:
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


def test_callback_redirects_when_code_exchange_raises():
    """A denied/expired/reused code makes the token endpoint reject the
    exchange; the round trip is unrecoverable from the browser."""

    async def exchange_code_for_claims(**_kwargs):
        raise RuntimeError("token endpoint returned 400")

    with routed(exchange=exchange_code_for_claims) as client:
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
            {"exchange": _no_email_exchange},
            {"code": "x", "state": "good-state"},
        ),
        (
            "email_not_verified",
            {"exchange": _unverified_email_exchange},
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


async def _no_email_exchange(**_kwargs):
    return {"email": None, "email_verified": True, "nonce": "the-nonce"}


async def _unverified_email_exchange(**_kwargs):
    return {
        "email": "agent@example.com",
        "email_verified": False,
        "nonce": "the-nonce",
    }


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    """Records added objects and replays canned results for `oidc_login`."""

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
            auth_services.oidc_login(
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
            auth_services.oidc_login(
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
            auth_services.oidc_login(
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
    `oidc_login` service to a FakeSession that already holds a User row for
    the callback's email, then asserts the callback succeeds and adds no
    new User to the session."""
    existing = User(email="agent@example.com")
    session = FakeSession(results=[[existing]])

    async def oidc_login(**kwargs):
        return await auth_services.oidc_login(**kwargs)

    with fake_session(session):
        with routed(oidc_login=oidc_login) as client:
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


def test_callback_normalises_the_email_like_the_email_flow():
    async def exchange_code_for_claims(**_kwargs):
        return {"email": "Agent@Example.COM", "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
        _callback(client)
    assert client._login_calls[0]["email"] == "Agent@example.com"


def test_callback_rejects_a_malformed_email_claim():
    async def exchange_code_for_claims(**_kwargs):
        return {"email": "not-an-address", "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
        response = _callback(client)
    assert _login_redirect(response) == "no_email"
    assert not client._login_calls


def test_callback_reports_a_deactivated_account():
    async def oidc_login(**_kwargs):
        return None

    with routed(oidc_login=oidc_login) as client:
        response = _callback(client)
    assert _login_redirect(response) == "account_unavailable"


def test_callback_redirects_when_the_client_secret_cannot_be_decrypted():
    def decrypt(_ciphertext):
        raise RuntimeError("OIDC_ENCRYPTION_KEY is not set")

    with routed(decrypt=decrypt) as client:
        response = _callback(client)
    assert _login_redirect(response) == "oidc_unavailable"
    assert not client._login_calls


def test_callback_passes_the_configured_issuer_to_the_code_exchange():
    seen = []

    async def exchange_code_for_claims(**kwargs):
        seen.append(kwargs)
        return {"email": "agent@example.com", "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
        _callback(client)
    assert seen[0]["issuer"] == "https://idp.example.test"
    assert seen[0]["client_id"] == "client-123"


def test_oidc_login_refuses_a_deactivated_account():
    deleted = User(email="gone@example.com", deleted_at=datetime.now())
    session = FakeSession(results=[[deleted]])
    with fake_session(session):
        signed_in = asyncio.run(
            auth_services.oidc_login(
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
