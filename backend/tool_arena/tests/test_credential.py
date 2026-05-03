"""Contract tests for the Credential Module (Phase 1 of OAuth refactor)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.tool_arena.config import (
    ApiKeyAuth,
    MCPServerConfig,
    NoAuth,
    OAuth2Auth,
)
from backend.tool_arena.credential import (
    ApiKeyCredential,
    Credential,
    CredentialMisconfigured,
    CredentialRevoked,
    NoneCredential,
    OAuth2Credential,
    _clear_credential_cache,
    credential_for,
)

pytestmark = pytest.mark.anyio


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_cache():
    _clear_credential_cache()
    yield
    _clear_credential_cache()


def _server(server_id: str = "srv", auth=None) -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="Server",
        description="test",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=auth,
    )


# --------------------------------------------------------------------------- #
# NoneCredential
# --------------------------------------------------------------------------- #


async def test_none_credential_returns_empty_headers():
    cred = NoneCredential()
    server = _server(auth=NoAuth(type="none"))
    assert await cred.headers_for(server) == {}


async def test_none_credential_works_when_auth_is_none():
    """server.auth=None is functionally equivalent to NoAuth."""
    cred = NoneCredential()
    server = _server(auth=None)
    assert await cred.headers_for(server) == {}


# --------------------------------------------------------------------------- #
# ApiKeyCredential
# --------------------------------------------------------------------------- #


async def test_api_key_credential_returns_configured_header(monkeypatch):
    monkeypatch.setenv("MY_KEY_ENV", "secret-123")
    server = _server(auth=ApiKeyAuth(type="api_key", key_env="MY_KEY_ENV", header="X-Api-Key"))
    cred = ApiKeyCredential()
    assert await cred.headers_for(server) == {"X-Api-Key": "secret-123"}


async def test_api_key_credential_default_header_is_authorization(monkeypatch):
    monkeypatch.setenv("MY_KEY_ENV", "abc")
    server = _server(auth=ApiKeyAuth(type="api_key", key_env="MY_KEY_ENV"))
    cred = ApiKeyCredential()
    assert await cred.headers_for(server) == {"Authorization": "abc"}


async def test_api_key_credential_raises_when_env_missing(monkeypatch):
    monkeypatch.delenv("MY_MISSING_KEY", raising=False)
    server = _server(auth=ApiKeyAuth(type="api_key", key_env="MY_MISSING_KEY"))
    cred = ApiKeyCredential()
    with pytest.raises(CredentialMisconfigured):
        await cred.headers_for(server)


async def test_api_key_credential_raises_on_wrong_auth_type():
    server = _server(auth=NoAuth(type="none"))
    cred = ApiKeyCredential()
    with pytest.raises(CredentialMisconfigured):
        await cred.headers_for(server)


# --------------------------------------------------------------------------- #
# OAuth2Credential
# --------------------------------------------------------------------------- #


def _oauth_server() -> MCPServerConfig:
    return _server(
        server_id="oauth_srv",
        auth=OAuth2Auth(
            type="oauth2",
            client_id="cid",
            client_secret_env="OAUTH_SECRET_ENV",
            token_url="https://example.com/token",
        ),
    )


async def test_oauth2_credential_returns_empty_headers_when_provider_ok():
    """OAuth lets the SDK manage Authorization via auth=provider — see module docstring."""
    server = _oauth_server()
    cred = OAuth2Credential()
    with patch("backend.tool_arena.auth.get_oauth_provider", return_value=object()):
        assert await cred.headers_for(server) == {}


async def test_oauth2_credential_translates_runtime_error_to_revoked():
    """RuntimeError from _redirect_handler => interactive flow needed => CredentialRevoked."""
    server = _oauth_server()
    cred = OAuth2Credential()
    with patch(
        "backend.tool_arena.auth.get_oauth_provider",
        side_effect=RuntimeError("OAuth authorization_code flow triggered..."),
    ):
        with pytest.raises(CredentialRevoked):
            await cred.headers_for(server)


async def test_oauth2_credential_raises_on_wrong_auth_type():
    server = _server(auth=NoAuth(type="none"))
    cred = OAuth2Credential()
    with pytest.raises(CredentialMisconfigured):
        await cred.headers_for(server)


async def test_oauth2_credential_provider_for_returns_cached_provider():
    server = _oauth_server()
    cred = OAuth2Credential()
    sentinel = object()
    with patch("backend.tool_arena.auth.get_oauth_provider", return_value=sentinel) as m:
        assert cred.provider_for(server) is sentinel
        m.assert_called_once_with(server)


# --------------------------------------------------------------------------- #
# Factory + cache
# --------------------------------------------------------------------------- #


def test_credential_for_dispatches_on_auth_type():
    none_srv = _server("a", auth=NoAuth(type="none"))
    api_srv = _server("b", auth=ApiKeyAuth(type="api_key", key_env="X"))
    oauth_srv = _server(
        "c",
        auth=OAuth2Auth(
            type="oauth2", client_id="cid", client_secret_env="S", token_url="https://x/t"
        ),
    )
    null_srv = _server("d", auth=None)

    assert isinstance(credential_for(none_srv), NoneCredential)
    assert isinstance(credential_for(api_srv), ApiKeyCredential)
    assert isinstance(credential_for(oauth_srv), OAuth2Credential)
    assert isinstance(credential_for(null_srv), NoneCredential)


def test_credential_for_caches_per_server_id():
    server = _server("cached", auth=NoAuth(type="none"))
    first = credential_for(server)
    second = credential_for(server)
    assert first is second


def test_credential_for_returns_distinct_instances_per_server_id():
    s1 = _server("one", auth=NoAuth(type="none"))
    s2 = _server("two", auth=NoAuth(type="none"))
    assert credential_for(s1) is not credential_for(s2)


def test_credential_protocol_runtime_check():
    """All Adapters satisfy the Credential Protocol structurally."""
    assert isinstance(NoneCredential(), Credential)
    assert isinstance(ApiKeyCredential(), Credential)
    assert isinstance(OAuth2Credential(), Credential)
