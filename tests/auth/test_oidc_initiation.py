"""
Tests for OIDC login initiation and the public auth config (no DB, no Redis,
no real identity provider).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_initiation.py
"""

import asyncio
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.oidc as oidc_module  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from tests.auth.fake_oidc_provider import (  # noqa: E402
    CLIENT_ID,
    ENCRYPTED_CLIENT_SECRET,
    ISSUER,
    FakeProvider,
    serving,
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


class FakeRedis:
    """Records what the state store wrote so a test can assert on it."""

    def __init__(self):
        self.store = {}
        self.counters = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key, seconds):
        pass


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


@contextlib.contextmanager
def routed(row=None, terms_accepted=True, provider=None):
    if row is None:
        row = _settings_row()
    if provider is None:
        provider = FakeProvider()

    async def get_app_settings():
        return row

    async def has_current_terms_acceptance(**_kwargs):
        return terms_accepted

    fake_redis = FakeRedis()

    with (
        serving(provider),
        patched(
            auth_router,
            get_app_settings=get_app_settings,
            has_current_terms_acceptance=has_current_terms_acceptance,
            get_redis_client=lambda: fake_redis,
        ),
    ):
        with patched(
            oidc_module,
            get_redis_client=lambda: fake_redis,
        ):
            app = FastAPI()
            app.include_router(auth_router.router)
            # The browser reaches the backend on the origin the provider is told
            # to come back to, as in a correct deployment.
            client = TestClient(app, base_url=auth_router.settings.api_origin)
            client.cookies.set("anonymous_session", "token")
            client._provider = provider  # type: ignore[attr-defined]
            yield client, fake_redis


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


def test_public_config_reports_oidc_disabled_when_the_secret_cannot_be_read():
    row = _settings_row(oidc_client_secret_encrypted=b"not-a-fernet-token")
    with patched(auth_router, get_app_settings=_as_async(row)):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is False


def test_public_config_reports_oidc_disabled_when_secret_missing():
    row = _settings_row(oidc_client_secret_encrypted=None)
    with patched(auth_router, get_app_settings=_as_async(row)):
        config = asyncio.run(auth_router.get_config())

    assert config.oidc_enabled is False


def test_oidc_login_redirects_to_the_provider_authorization_endpoint():
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
        f"{auth_router.settings.api_origin}/api/auth/oidc/callback"
    ]
    assert params["scope"] == ["openid email"]
    assert len(params["state"][0]) >= 32
    assert len(params["nonce"][0]) >= 32
    # state and nonce are stored server-side, linked by the same key.
    state = params["state"][0]
    stored = json.loads(fake_redis.store[_oidc_state_key(state)])
    assert stored == {"nonce": params["nonce"][0], "redirect": "/", "merge": False}
    assert len(client._provider.requests_to("/.well-known/openid-configuration")) == 1
    # The browser keeps the state too, so the callback can tell it apart from
    # a state issued to someone else.
    set_cookie = response.headers["set-cookie"]
    assert f"oidc_state={state}" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    assert "path=/api/auth/oidc" in set_cookie.lower()


def test_oidc_login_refuses_when_the_request_origin_is_not_the_callback_origin(caplog):
    # The state cookie is set for the origin the login came in on; a callback on
    # another origin could never send it back, so fail now instead of after the
    # provider round trip.
    with routed() as (client, fake_redis):
        client.base_url = "http://elsewhere.example.test"
        with caplog.at_level(logging.ERROR):
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "oidc_unavailable"
    assert not client._provider.requests
    assert not fake_redis.store
    assert "oidc_state" not in response.headers.get("set-cookie", "")
    assert (
        "http://elsewhere.example.test",
        auth_router.settings.api_origin,
    ) in [record.args for record in caplog.records]


def test_oidc_login_reads_the_origin_from_the_proxy_headers():
    # Behind the ingress the backend sees an internal host over plain http.
    with patched(auth_router.settings, COMPARIA_API_URL="https://arena.example.test"):
        with routed() as (client, _fake_redis):
            client.base_url = "http://backend.internal"
            response = client.get(
                "/auth/oidc/login",
                follow_redirects=False,
                headers={
                    "x-forwarded-host": "arena.example.test",
                    "x-forwarded-proto": "https",
                },
            )

    assert response.status_code == 302
    assert urlsplit(response.headers["location"]).netloc == "idp.example.test"


def test_oidc_login_ignores_a_default_port_and_letter_case_in_the_origin():
    with patched(auth_router.settings, COMPARIA_API_URL="https://Arena.example.test"):
        with routed() as (client, _fake_redis):
            client.base_url = "https://arena.example.test:443"
            response = client.get("/auth/oidc/login", follow_redirects=False)

    assert urlsplit(response.headers["location"]).netloc == "idp.example.test"


def test_oidc_login_requires_terms_acceptance_before_any_redirect():
    with routed(terms_accepted=False) as (client, _fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert (
        not client._provider.requests
    ), "the provider was called before the terms gate"

    # Reached from a browser link: resolves to a redirect the login page
    # renders, not a JSON error page.
    assert response.status_code == 302
    location = response.headers["location"]
    assert "error=terms_required" in location
    assert location.startswith(auth_router.settings.COMPARIA_APP_URL)


def test_oidc_login_rejects_when_oidc_disabled_in_methods():
    row = _settings_row(auth_methods=["email_code"])
    with routed(row=row) as (client, _fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "oidc_unavailable"
    assert not client._provider.requests


def test_oidc_login_rejects_when_provider_unconfigured():
    row = _settings_row(
        oidc_issuer=None, oidc_client_id=None, oidc_client_secret_encrypted=None
    )
    with routed(row=row) as (client, _fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "oidc_unavailable"
    assert not client._provider.requests


def test_oidc_login_rejects_when_the_client_secret_cannot_be_read():
    row = _settings_row(oidc_client_secret_encrypted=b"not-a-fernet-token")
    with routed(row=row) as (client, _fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "oidc_unavailable"
    assert not client._provider.requests


def test_oidc_login_rejects_when_discovery_has_no_authorization_endpoint():
    provider = FakeProvider()
    provider.discovery = {"issuer": ISSUER}
    with routed(provider=provider) as (client, fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "provider_error"
    assert not fake_redis.store


def test_oidc_login_redirects_back_when_discovery_fails():
    provider = FakeProvider()
    provider.unreachable = True
    with routed(provider=provider) as (client, _fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "provider_error"
    assert "oidc_state" not in response.headers.get("set-cookie", "")


def test_oidc_login_refuses_a_non_https_authorization_endpoint():
    provider = FakeProvider()
    provider.discovery["authorization_endpoint"] = "http://idp.example.test/authorize"
    with routed(provider=provider) as (client, fake_redis):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert _error_param(response) == "provider_error"
    assert not fake_redis.store
    assert "oidc_state" not in response.headers.get("set-cookie", "")


def test_oidc_login_accepts_plain_http_endpoints_on_localhost():
    """The local Keycloak keeps working."""
    local = "http://localhost:8080"
    provider = FakeProvider()
    provider.discovery = {
        "issuer": local,
        "authorization_endpoint": f"{local}/authorize",
        "token_endpoint": f"{local}/token",
        "userinfo_endpoint": f"{local}/userinfo",
    }
    with routed(_settings_row(oidc_issuer=local), provider=provider) as (
        client,
        _fake_redis,
    ):
        response = client.get("/auth/oidc/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith(f"{local}/authorize?")


def test_oidc_login_keeps_where_to_land_and_whether_to_merge():
    with routed() as (client, fake_redis):
        response = client.get(
            "/auth/oidc/login",
            params={"redirect": "/arena?x=1", "merge": "1"},
            follow_redirects=False,
        )

    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    stored = json.loads(fake_redis.store[_oidc_state_key(state)])
    assert stored["redirect"] == "/arena?x=1"
    assert stored["merge"] is True


def test_oidc_login_ignores_an_off_site_redirect():
    for redirect in ("https://evil.test/", "//evil.test", "/\\evil.test", "arena"):
        with routed() as (client, fake_redis):
            response = client.get(
                "/auth/oidc/login",
                params={"redirect": redirect},
                follow_redirects=False,
            )

        state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
        stored = json.loads(fake_redis.store[_oidc_state_key(state)])
        assert stored["redirect"] == "/", redirect


def test_oidc_login_is_rate_limited_per_ip():
    with patched(auth_router.settings, AUTH_OIDC_LOGIN_PER_IP_PER_HOUR=2):
        with routed() as (client, _fake_redis):
            responses = [
                client.get("/auth/oidc/login", follow_redirects=False) for _ in range(3)
            ]

    assert [urlsplit(r.headers["location"]).netloc for r in responses[:2]] == [
        "idp.example.test",
        "idp.example.test",
    ]
    assert _error_param(responses[2]) == "rate_limited"


def _error_param(response):
    assert response.status_code == 302, response.text
    location = response.headers["location"]
    assert location.startswith(f"{auth_router.settings.COMPARIA_APP_URL}/login?")
    return parse_qs(urlsplit(location).query)["error"][0]


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
