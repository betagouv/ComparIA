"""Unit tests for OAuth2 auth module (MCP SDK OAuthClientProvider-based)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

import pytest

from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

import backend.tool_arena.auth as auth_module
from backend.tool_arena.config import MCPServerConfig, OAuth2Auth

pytestmark = pytest.mark.anyio


def _make_server(tmp_path: Path) -> MCPServerConfig:
    return MCPServerConfig(
        id="test_srv",
        name="Test Server",
        description="test",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=OAuth2Auth(
            type="oauth2",
            client_id="test_client_id",
            client_secret_env="TEST_SECRET",
            token_url="https://example.com/o/token/",
        ),
    )


@pytest.fixture(autouse=True)
def clear_cache():
    auth_module._clear_token_cache()
    yield
    auth_module._clear_token_cache()


@pytest.fixture
def force_file_storage(tmp_path):
    """Force FileTokenStorage by making _get_storage return it."""
    def _file_storage(server_id):
        return auth_module.FileTokenStorage(server_id)
    with patch.object(auth_module, "_get_storage", _file_storage):
        with patch.object(auth_module, "TOKENS_DIR", tmp_path):
            yield tmp_path


async def test_file_token_storage_roundtrip(tmp_path):
    """FileTokenStorage stores and retrieves tokens."""
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage("srv1")
        assert await storage.get_tokens() is None

        from mcp.shared.auth import OAuthToken
        token = OAuthToken(access_token="abc123", token_type="Bearer")
        await storage.set_tokens(token)

        retrieved = await storage.get_tokens()
        assert retrieved is not None
        assert retrieved.access_token == "abc123"


async def test_file_token_storage_client_info_roundtrip(tmp_path):
    """FileTokenStorage stores and retrieves client info."""
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage("srv1")
        assert await storage.get_client_info() is None

        from mcp.shared.auth import OAuthClientInformationFull
        info = OAuthClientInformationFull(
            client_id="cid",
            redirect_uris=["http://localhost:9876/callback"],
        )
        await storage.set_client_info(info)

        retrieved = await storage.get_client_info()
        assert retrieved is not None
        assert retrieved.client_id == "cid"


def test_build_oauth_provider_returns_provider(force_file_storage):
    """build_oauth_provider returns an OAuthClientProvider with pre-seeded client info."""
    tmp_path = force_file_storage
    server = _make_server(tmp_path)
    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        from mcp.client.auth import OAuthClientProvider
        provider = auth_module.build_oauth_provider(server)
        assert isinstance(provider, OAuthClientProvider)


def test_bootstrap_tokens_from_env(tmp_path):
    """_bootstrap_tokens_from_env pre-seeds tokens.json from env var."""
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        with patch.dict("os.environ", {"TEST_SRV_REFRESH_TOKEN": "my_refresh_tok"}):
            auth_module._bootstrap_tokens_from_env(server, storage)

        tokens_path = tmp_path / "test_srv" / "tokens.json"
        assert tokens_path.exists()
        data = json.loads(tokens_path.read_text())
        assert data["refresh_token"] == "my_refresh_tok"
        assert data["access_token"] == ""


def test_bootstrap_skips_if_tokens_match(tmp_path):
    """_bootstrap_tokens_from_env does not overwrite when refresh_token matches env."""
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        tokens_path = tmp_path / "test_srv" / "tokens.json"
        tokens_path.write_text(
            '{"access_token":"real","token_type":"Bearer","refresh_token":"same_token"}'
        )

        with patch.dict("os.environ", {"TEST_SRV_REFRESH_TOKEN": "same_token"}):
            auth_module._bootstrap_tokens_from_env(server, storage)

        data = json.loads(tokens_path.read_text())
        assert data["access_token"] == "real"
        assert data["refresh_token"] == "same_token"


def test_bootstrap_does_not_overwrite_rotated_refresh_token(tmp_path):
    """Bootstrap MUST NOT overwrite a stored refresh_token, even when env var differs.

    Many OAuth providers rotate refresh_tokens; the env var is the original
    bootstrap value and is revoked after the first successful refresh.
    Overwriting on restart would replay the revoked token.
    """
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        tokens_path = tmp_path / "test_srv" / "tokens.json"
        # Simulate state after a successful SDK refresh: rotated refresh_token,
        # real access_token in storage.
        tokens_path.write_text(
            '{"access_token":"real_access","token_type":"Bearer","refresh_token":"rotated_token"}'
        )

        with patch.dict("os.environ", {"TEST_SRV_REFRESH_TOKEN": "original_revoked_token"}):
            auth_module._bootstrap_tokens_from_env(server, storage)

        data = json.loads(tokens_path.read_text())
        # Storage must be untouched
        assert data["refresh_token"] == "rotated_token"
        assert data["access_token"] == "real_access"


def test_bootstrap_does_not_overwrite_pristine_bootstrap(tmp_path):
    """Even a pristine bootstrap (empty access_token) is not re-overwritten.

    Once any refresh_token is in storage, the env var bootstrap is a no-op.
    To force a re-seed, callers must clear storage first.
    """
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        tokens_path = tmp_path / "test_srv" / "tokens.json"
        tokens_path.write_text(
            '{"access_token":"","token_type":"Bearer","refresh_token":"existing_bootstrap"}'
        )

        with patch.dict("os.environ", {"TEST_SRV_REFRESH_TOKEN": "different_value"}):
            auth_module._bootstrap_tokens_from_env(server, storage)

        data = json.loads(tokens_path.read_text())
        assert data["refresh_token"] == "existing_bootstrap"


def test_bootstrap_skips_if_no_env_var(tmp_path):
    """_bootstrap_tokens_from_env is a no-op without the env var."""
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        auth_module._bootstrap_tokens_from_env(server, storage)
        tokens_path = tmp_path / "test_srv" / "tokens.json"
        assert not tokens_path.exists()


def test_get_oauth_provider_caches(force_file_storage):
    """get_oauth_provider returns same instance on repeated calls."""
    server = _make_server(force_file_storage)
    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        p1 = auth_module.get_oauth_provider(server)
        p2 = auth_module.get_oauth_provider(server)
        assert p1 is p2


def test_clear_token_cache():
    """_clear_token_cache empties the provider cache."""
    auth_module._provider_cache["dummy"] = "fake"
    assert len(auth_module._provider_cache) == 1
    auth_module._clear_token_cache()
    assert len(auth_module._provider_cache) == 0


# --- CompaRAGOAuthProvider._refresh_token() tests ---

def _build_provider(tmp_path, token_url="https://example.com/o/token/"):
    """Build a CompaRAGOAuthProvider with FileTokenStorage for testing."""
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage("test_srv")
    client_metadata = OAuthClientMetadata(
        redirect_uris=["http://localhost:9876/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        client_name="test",
    )
    return auth_module.CompaRAGOAuthProvider(
        token_url=token_url,
        server_url="https://example.com/mcp",
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=None,
        callback_handler=None,
    )


async def test_refresh_token_uses_configured_token_url(tmp_path):
    """_refresh_token() sends to configured token_url, not SDK fallback."""
    provider = _build_provider(tmp_path, token_url="https://example.com/o/token/")
    provider.context.current_tokens = OAuthToken(
        access_token="", token_type="Bearer", refresh_token="test_refresh"
    )
    provider.context.client_info = OAuthClientInformationFull(
        client_id="test_id", redirect_uris=["http://localhost:9876/callback"]
    )
    request = await provider._refresh_token()
    assert str(request.url) == "https://example.com/o/token/"
    assert request.method == "POST"


async def test_refresh_token_includes_correct_form_data(tmp_path):
    """_refresh_token() includes grant_type, refresh_token, client_id in body."""
    provider = _build_provider(tmp_path)
    provider.context.current_tokens = OAuthToken(
        access_token="", token_type="Bearer", refresh_token="my_refresh"
    )
    provider.context.client_info = OAuthClientInformationFull(
        client_id="my_client", redirect_uris=["http://localhost:9876/callback"]
    )
    request = await provider._refresh_token()
    body = parse_qs(request.content.decode())
    assert body["grant_type"] == ["refresh_token"]
    assert body["refresh_token"] == ["my_refresh"]
    assert body["client_id"] == ["my_client"]


async def test_refresh_prefers_discovered_metadata(tmp_path):
    """If OAuth metadata is discovered, its token_endpoint takes priority."""
    from mcp.shared.auth import OAuthMetadata

    provider = _build_provider(tmp_path, token_url="https://configured.example.com/o/token/")
    provider.context.current_tokens = OAuthToken(
        access_token="", token_type="Bearer", refresh_token="test_refresh"
    )
    provider.context.client_info = OAuthClientInformationFull(
        client_id="test_id", redirect_uris=["http://localhost:9876/callback"]
    )
    provider.context.oauth_metadata = OAuthMetadata(
        issuer="https://discovered.example.com",
        authorization_endpoint="https://discovered.example.com/authorize",
        token_endpoint="https://discovered.example.com/token",
        response_types_supported=["code"],
    )
    request = await provider._refresh_token()
    assert "discovered.example.com" in str(request.url)


async def test_refresh_raises_without_tokens(tmp_path):
    """_refresh_token() raises OAuthTokenError when no tokens are seeded."""
    from mcp.client.auth.exceptions import OAuthTokenError

    provider = _build_provider(tmp_path)
    provider.context.client_info = OAuthClientInformationFull(
        client_id="test_id", redirect_uris=["http://localhost:9876/callback"]
    )
    with pytest.raises(OAuthTokenError):
        await provider._refresh_token()


async def test_build_oauth_provider_client_info_has_auth_method(force_file_storage):
    """build_oauth_provider pre-seeds client_info with token_endpoint_auth_method."""
    server = _make_server(force_file_storage)
    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        provider = auth_module.build_oauth_provider(server)

    await provider._initialize()
    assert provider.context.client_info is not None
    assert provider.context.client_info.token_endpoint_auth_method == "client_secret_post"
    assert provider.context.client_info.client_secret == "secret_value"


def test_build_oauth_provider_missing_secret_preserves_stored_client_info(
    force_file_storage, caplog
):
    """When the secret env var is missing, stored client_info must NOT be overwritten."""
    tmp_path = force_file_storage
    server = _make_server(tmp_path)
    server_dir = tmp_path / server.id
    server_dir.mkdir(parents=True, exist_ok=True)
    stored = OAuthClientInformationFull(
        client_id="test_client_id",
        client_secret="previously_valid_secret",
        redirect_uris=["http://localhost:9876/callback"],
        token_endpoint_auth_method="client_secret_post",
    )
    (server_dir / "client_info.json").write_text(stored.model_dump_json(indent=2))

    with patch.dict("os.environ", {}, clear=False):
        # Make absolutely sure TEST_SECRET is not set
        import os
        os.environ.pop("TEST_SECRET", None)
        provider = auth_module.build_oauth_provider(server)

    # Stored secret must still be intact
    on_disk = json.loads((server_dir / "client_info.json").read_text())
    assert on_disk["client_secret"] == "previously_valid_secret"
    assert provider is not None


async def test_prewarm_skips_non_oauth_servers(tmp_path):
    """prewarm_oauth_provider returns True without calling MCP for non-OAuth servers."""
    server = MCPServerConfig(
        id="plain",
        name="Plain",
        description="x",
        endpoint="http://example.com/mcp",
        transport="streamablehttp",
    )
    assert await auth_module.prewarm_oauth_provider(server) is True


async def test_prewarm_all_no_oauth_servers_is_noop():
    """prewarm_all_oauth_providers does nothing when no OAuth server is registered."""
    server = MCPServerConfig(
        id="plain",
        name="Plain",
        description="x",
        endpoint="http://example.com/mcp",
        transport="streamablehttp",
    )
    # Should complete without error and without raising even with empty list
    await auth_module.prewarm_all_oauth_providers([])
    await auth_module.prewarm_all_oauth_providers([server])


async def test_prewarm_swallows_oauth_handshake_failure(tmp_path, caplog):
    """prewarm_oauth_provider returns False (not raises) when the handshake fails."""
    import logging

    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
            with caplog.at_level(logging.WARNING, logger="languia"):
                # No real Clarifeye server is reachable at example.com → handshake
                # will time out or refuse connection. Either way prewarm must
                # not raise — startup must continue.
                result = await asyncio.wait_for(
                    auth_module.prewarm_oauth_provider(server),
                    timeout=auth_module.PREWARM_TIMEOUT_SECONDS + 5,
                )
    assert result is False


def test_build_oauth_provider_missing_secret_no_stored_info_logs_error(
    force_file_storage, caplog
):
    """Missing env var AND no stored client_info should log an error and not write garbage."""
    import logging
    import os

    tmp_path = force_file_storage
    server = _make_server(tmp_path)

    os.environ.pop("TEST_SECRET", None)
    with caplog.at_level(logging.ERROR, logger="languia"):
        provider = auth_module.build_oauth_provider(server)

    server_dir = tmp_path / server.id
    assert not (server_dir / "client_info.json").exists()
    assert provider is not None
    assert any("misconfiguration" in r.message.lower() for r in caplog.records)
