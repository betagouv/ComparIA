"""
Tests for the OIDC callback (no DB, no Redis, no real identity provider).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_callback.py
"""

import asyncio
import contextlib
import os
import sys
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


@contextlib.contextmanager
def routed(row=None, stored_nonce="the-nonce", exchange=None, discover=None, oidc_login=None):
    if row is None:
        row = _settings_row()

    async def get_app_settings():
        return row

    def consume_state(state):
        # Tests reuse a single in-flight state; the router only calls this
        # once per request, so returning the stored nonce is enough.
        return stored_nonce if state == "good-state" else None

    if discover is None:

        async def discover_provider(_issuer):
            return _discovery()

    else:
        discover_provider = discover

    if exchange is None:

        async def exchange_code_for_claims(**_kwargs):
            return {"email": "agent@example.test", "nonce": "the-nonce"}

    else:
        exchange_code_for_claims = exchange

    # Spy: records whether the happy-path `oidc_login` service ran. Failure
    # paths must never reach it (no User row, no session minted).
    login_calls = []

    if oidc_login is None:

        async def oidc_login_service(**kwargs):
            login_calls.append(kwargs)
            return "session-token"

    else:
        oidc_login_service = oidc_login

    def decrypt_oidc_secret(_ciphertext):
        return "super-secret"

    with patched(
        auth_router,
        get_app_settings=get_app_settings,
        consume_state=consume_state,
        discover_provider=discover_provider,
        exchange_code_for_claims=exchange_code_for_claims,
        oidc_login_service=oidc_login_service,
        decrypt_oidc_secret=decrypt_oidc_secret,
    ):
        app = FastAPI()
        app.include_router(auth_router.router)
        client = TestClient(app)
        client.cookies.set("anonymous_session", "token")
        # Expose the spy without changing the `routed() as client` convention.
        client._login_calls = login_calls  # type: ignore[attr-defined]
        yield client


def _login_redirect(response):
    """A failure-path response: 302 to /login?error=..., no session cookie."""
    assert response.status_code == 302, response.text
    from urllib.parse import parse_qs, urlsplit

    parsed = urlsplit(response.headers["location"])
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
    assert response.headers["location"] == "/"
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
        return {"email": "agent@example.test", "nonce": "different-nonce"}

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
        return {"email": None, "nonce": "the-nonce"}

    with routed(exchange=exchange_code_for_claims) as client:
        response = client.get(
            "/auth/oidc/callback",
            params={"code": "auth-code", "state": "good-state"},
            follow_redirects=False,
        )
    reason = _login_redirect(response)
    assert reason == "no_email"
    assert not client._login_calls


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
    return {"email": None, "nonce": "the-nonce"}


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
                email="newcomer@example.test",
                ip="127.0.0.1",
                user_agent=None,
                visitor_id=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert session.committed
    assert any(isinstance(obj, User) for obj in session.added)
    created = next(obj for obj in session.added if isinstance(obj, User))
    assert created.email == "newcomer@example.test"
    assert created.role == "user"


def test_oidc_login_reuses_an_existing_account_instead_of_duplicating_it():
    existing = User(email="agent@example.test")
    session = FakeSession(results=[[existing]])
    with fake_session(session):
        token = asyncio.run(
            auth_services.oidc_login(
                email="agent@example.test",
                ip="127.0.0.1",
                user_agent=None,
                visitor_id=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert session.committed
    assert not any(isinstance(obj, User) for obj in session.added)


def test_oidc_login_lands_on_a_pre_seeded_admin_account():
    admin = User(email="boss@example.test", role="admin")
    session = FakeSession(results=[[admin]])
    with fake_session(session):
        token = asyncio.run(
            auth_services.oidc_login(
                email="boss@example.test",
                ip="127.0.0.1",
                user_agent=None,
                visitor_id=None,
                anonymous_user_hash=None,
            )
        )

    assert token
    assert admin.role == "admin"
    assert not any(isinstance(obj, User) for obj in session.added)


def test_callback_reuses_an_existing_account_instead_of_duplicating_it():
    """Router-seam test (spec: 'an existing email-code account is reused
    when the same email authenticates via OIDC'). Wires the real
    `oidc_login` service to a FakeSession that already holds a User row for
    the callback's email, then asserts the callback succeeds and adds no
    new User to the session."""
    existing = User(email="agent@example.test")
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
    assert response.headers["location"] == "/"
    assert "auth_session=" in response.headers["set-cookie"]
    assert not any(isinstance(obj, User) for obj in session.added)


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
