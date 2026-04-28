"""Unit tests for OAuth2 auth module (MCP SDK OAuthClientProvider-based)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

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


def test_bootstrap_skips_if_tokens_exist(tmp_path):
    """_bootstrap_tokens_from_env does not overwrite existing tokens."""
    server = _make_server(tmp_path)
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage(server.id)
        tokens_path = tmp_path / "test_srv" / "tokens.json"
        tokens_path.write_text('{"access_token":"real","token_type":"Bearer"}')

        with patch.dict("os.environ", {"TEST_SRV_REFRESH_TOKEN": "should_not_write"}):
            auth_module._bootstrap_tokens_from_env(server, storage)

        data = json.loads(tokens_path.read_text())
        assert data["access_token"] == "real"
        assert "refresh_token" not in data


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
