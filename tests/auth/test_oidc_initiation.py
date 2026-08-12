"""
Tests for OIDC login initiation and the public auth config (no DB, no Redis,
no real identity provider).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_initiation.py
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.oidc as oidc_module  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router


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


class FakeRedis:
    """Records what the state store wrote so a test can assert on it."""

    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True


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


@contextlib.contextmanager
def routed(row=None, terms_accepted=True):
    if row is None:
        row = _settings_row()

    async def get_app_settings():
        return row

    async def has_current_terms_acceptance(**_kwargs):
        return terms_accepted

    fake_redis = FakeRedis()

    with patched(
        auth_router,
        get_app_settings=get_app_settings,
        has_current_terms_acceptance=has_current_terms_acceptance,
    ):
        with patched(
            oidc_module,
            get_redis_client=lambda: fake_redis,
        ):
            app = FastAPI()
            app.include_router(auth_router.router)
            client = TestClient(app)
            client.cookies.set("anonymous_session", "token")
            yield client, fake_redis


def _discovery():
    return {
        "issuer": "https://idp.example.test",
        "authorization_endpoint": "https://idp.example.test/authorize",
        "token_endpoint": "https://idp.example.test/token",
        "userinfo_endpoint": "https://idp.example.test/userinfo",
    }


def test_public_config_reports_oidc_enabled_when_configured():
    with patched(auth_router, get_app_settings=_as_async(_settings_row())):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is True
    assert config.oidc_button_label == "Se connecter avec ProConnect"
    assert config.oidc_has_button_logo is True
    assert config.methods == ["email_code", "oidc"]


def test_public_config_reports_oidc_disabled_when_not_in_methods():
    row = _settings_row(auth_methods=["email_code"])
    with patched(auth_router, get_app_settings=_as_async(row)):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is False


def test_public_config_reports_oidc_disabled_when_provider_unconfigured():
    row = _settings_row(
        oidc_issuer=None, oidc_client_id=None, oidc_client_secret_encrypted=None
    )
    with patched(auth_router, get_app_settings=_as_async(row)):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is False
    assert config.methods == ["email_code", "oidc"]


def test_public_config_reports_oidc_disabled_when_secret_missing():
    row = _settings_row(oidc_client_secret_encrypted=None)
    with patched(auth_router, get_app_settings=_as_async(row)):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is False


def test_oidc_login_redirects_to_the_provider_authorization_endpoint():
    discovered = []

    async def discover_provider(issuer):
        discovered.append(issuer)
        return _discovery()

    with patched(auth_router, discover_provider=discover_provider):
        with routed() as (client, fake_redis):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    parsed = urlsplit(location)
    assert parsed.scheme == "https"
    assert parsed.netloc == "idp.example.test"
    assert parsed.path == "/authorize"
    params = parse_qs(parsed.query)
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["client-123"]
    assert params["redirect_uri"] == [
        f"{auth_router.settings.COMPARIA_APP_URL}/auth/oidc/callback"
    ]
    assert params["scope"] == ["openid email"]
    assert len(params["state"][0]) >= 32
    assert len(params["nonce"][0]) >= 32
    # state and nonce are stored server-side, linked by the same key.
    assert fake_redis.store
    state = params["state"][0]
    assert fake_redis.store[_oidc_state_key(state)] == params["nonce"][0]
    assert discovered == ["https://idp.example.test"]


def test_oidc_login_requires_terms_acceptance_before_any_redirect():
    async def discover_provider(_issuer):
        raise AssertionError("discovery ran before the terms gate")

    with patched(auth_router, discover_provider=discover_provider):
        with routed(terms_accepted=False) as (client, _fake_redis):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 428


def test_oidc_login_rejects_when_oidc_disabled_in_methods():
    async def discover_provider(_issuer):
        raise AssertionError("discovery ran on a disabled method")

    row = _settings_row(auth_methods=["email_code"])
    with patched(auth_router, discover_provider=discover_provider):
        with routed(row=row) as (client, _fake_redis):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 400
    assert "not enabled" in response.json()["detail"].lower()


def test_oidc_login_rejects_when_provider_unconfigured():
    async def discover_provider(_issuer):
        raise AssertionError("discovery ran on an unconfigured provider")

    row = _settings_row(
        oidc_issuer=None, oidc_client_id=None, oidc_client_secret_encrypted=None
    )
    with patched(auth_router, discover_provider=discover_provider):
        with routed(row=row) as (client, _fake_redis):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 400


def test_oidc_login_rejects_when_discovery_has_no_authorization_endpoint():
    async def discover_provider(_issuer):
        return {"issuer": "https://idp.example.test"}

    with patched(auth_router, discover_provider=discover_provider):
        with routed() as (client, _fake_redis):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 502


def _oidc_state_key(state):
    from utils.storage.redis import REDIS_OIDC_STATE_PREFIX

    return REDIS_OIDC_STATE_PREFIX + state


def _as_async(row):
    async def get_app_settings():
        return row

    return get_app_settings


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
