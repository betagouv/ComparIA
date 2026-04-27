"""Unit tests for env var URL overlay and extended config schema in load_mcp_servers()."""

import json
import os
import pytest
from pathlib import Path

from backend.tool_arena.config import load_mcp_servers


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _write_mcp_servers_json(tmp_path: Path, extra_entries: list | None = None) -> Path:
    """Write a temporary mcp_servers.json with localhost defaults."""
    data = [
        {
            "id": "langchain_rag",
            "name": "LangChain RAG",
            "description": "RAG pipeline using LangChain",
            "endpoint": "http://localhost:8010/mcp",
            "transport": "streamablehttp",
            "tools": ["*"],
        },
        {
            "id": "llamaindex_rag",
            "name": "LlamaIndex RAG",
            "description": "RAG pipeline using LlamaIndex",
            "endpoint": "http://localhost:8011/mcp",
            "transport": "streamablehttp",
            "tools": ["*"],
        },
    ]
    if extra_entries:
        data.extend(extra_entries)
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(json.dumps(data))
    return config_path


# --------------------------------------------------------------------------- #
# Existing overlay tests (backward compat)
# --------------------------------------------------------------------------- #

def test_overlay_applies_env_var(tmp_path, monkeypatch):
    """Test 1: When MCP_LANGCHAIN_RAG_URL is set, load_mcp_servers() uses it."""
    monkeypatch.setenv(
        "MCP_LANGCHAIN_RAG_URL",
        "http://langchain-rag.railway.internal:8010/mcp",
    )
    config_path = _write_mcp_servers_json(tmp_path)
    servers = load_mcp_servers(config_path)
    langchain = next(s for s in servers if s.id == "langchain_rag")
    assert str(langchain.endpoint) == "http://langchain-rag.railway.internal:8010/mcp"


def test_overlay_no_env_var_keeps_default(tmp_path, monkeypatch):
    """Test 2: When no env vars are set, load_mcp_servers() returns localhost defaults."""
    monkeypatch.delenv("MCP_LANGCHAIN_RAG_URL", raising=False)
    monkeypatch.delenv("MCP_LLAMAINDEX_RAG_URL", raising=False)
    config_path = _write_mcp_servers_json(tmp_path)
    servers = load_mcp_servers(config_path)
    langchain = next(s for s in servers if s.id == "langchain_rag")
    assert str(langchain.endpoint) == "http://localhost:8010/mcp"


def test_overlay_invalid_url_raises(tmp_path, monkeypatch):
    """Test 3: When env var is set to an invalid URL, load_mcp_servers() raises ValidationError."""
    from pydantic import ValidationError

    monkeypatch.setenv("MCP_LANGCHAIN_RAG_URL", "not-a-url")
    config_path = _write_mcp_servers_json(tmp_path)
    with pytest.raises(ValidationError):
        load_mcp_servers(config_path)


def test_overlay_partial(tmp_path, monkeypatch):
    """Test 4: When only MCP_LLAMAINDEX_RAG_URL is set, langchain_rag stays localhost, llamaindex_rag is overridden."""
    monkeypatch.delenv("MCP_LANGCHAIN_RAG_URL", raising=False)
    monkeypatch.setenv(
        "MCP_LLAMAINDEX_RAG_URL",
        "http://llamaindex-rag.railway.internal:8011/mcp",
    )
    config_path = _write_mcp_servers_json(tmp_path)
    servers = load_mcp_servers(config_path)
    langchain = next(s for s in servers if s.id == "langchain_rag")
    llamaindex = next(s for s in servers if s.id == "llamaindex_rag")
    assert str(langchain.endpoint) == "http://localhost:8010/mcp"
    assert str(llamaindex.endpoint) == "http://llamaindex-rag.railway.internal:8011/mcp"


# --------------------------------------------------------------------------- #
# New auth union tests (D-01)
# --------------------------------------------------------------------------- #

def test_oauth2_auth_validates(tmp_path):
    """Test 5: MCPAuthConfig with type='oauth2' validates client_id, client_secret_env, token_url."""
    from backend.tool_arena.config import OAuth2Auth

    auth = OAuth2Auth(
        type="oauth2",
        client_id="my_client",
        client_secret_env="CLARIFEYE_CLIENT_SECRET",
        token_url="https://auth.example.com/token",
    )
    assert auth.type == "oauth2"
    assert auth.client_id == "my_client"
    assert auth.client_secret_env == "CLARIFEYE_CLIENT_SECRET"
    assert auth.token_url == "https://auth.example.com/token"


def test_api_key_auth_validates(tmp_path):
    """Test 6: MCPAuthConfig with type='api_key' validates key_env and header fields."""
    from backend.tool_arena.config import ApiKeyAuth

    auth = ApiKeyAuth(type="api_key", key_env="RAGIE_API_KEY", header="X-API-Key")
    assert auth.type == "api_key"
    assert auth.key_env == "RAGIE_API_KEY"
    assert auth.header == "X-API-Key"


def test_api_key_auth_default_header(tmp_path):
    """Test 6b: ApiKeyAuth uses 'Authorization' as default header."""
    from backend.tool_arena.config import ApiKeyAuth

    auth = ApiKeyAuth(type="api_key", key_env="RAGIE_API_KEY")
    assert auth.header == "Authorization"


def test_no_auth_validates(tmp_path):
    """Test 7: MCPAuthConfig with type='none' requires no extra fields."""
    from backend.tool_arena.config import NoAuth

    auth = NoAuth(type="none")
    assert auth.type == "none"


def test_invalid_auth_type_raises(tmp_path):
    """Test 8: Invalid auth type raises ValidationError."""
    from backend.tool_arena.config import MCPServerConfig
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MCPServerConfig(
            id="bad_server",
            name="Bad Server",
            description="test",
            endpoint="http://localhost:9000/mcp",
            transport="streamablehttp",
            auth={"type": "invalid_type"},
        )


def test_server_config_accepts_sanitize_block(tmp_path):
    """Test 9: MCPServerConfig accepts optional sanitize block."""
    from backend.tool_arena.config import MCPServerConfig, SanitizeConfig

    server = MCPServerConfig(
        id="clarifeye",
        name="Clarifeye",
        description="RAG tool",
        endpoint="http://localhost:9001/mcp",
        transport="streamablehttp",
        sanitize=SanitizeConfig(
            url_patterns=["https://clarifeye\\..*"],
            metadata_keys=["source_id", "doc_id"],
            extra_terms=["Clarifeye", "clarifeye"],
        ),
    )
    assert server.sanitize is not None
    assert len(server.sanitize.url_patterns) == 1
    assert len(server.sanitize.metadata_keys) == 2
    assert len(server.sanitize.extra_terms) == 2


def test_sanitize_config_defaults_to_empty_lists(tmp_path):
    """Test 9b: SanitizeConfig with no fields uses empty lists."""
    from backend.tool_arena.config import SanitizeConfig

    sc = SanitizeConfig()
    assert sc.url_patterns == []
    assert sc.metadata_keys == []
    assert sc.extra_terms == []


def test_convention_url_override_new_server(tmp_path, monkeypatch):
    """Test 10: Convention-based URL override derives env var from server id (clarifeye -> MCP_CLARIFEYE_URL)."""
    monkeypatch.setenv("MCP_CLARIFEYE_URL", "http://clarifeye.railway.internal/mcp")
    monkeypatch.delenv("MCP_LANGCHAIN_RAG_URL", raising=False)
    monkeypatch.delenv("MCP_LLAMAINDEX_RAG_URL", raising=False)

    extra = [
        {
            "id": "clarifeye",
            "name": "Clarifeye RAG",
            "description": "Clarifeye RAG pipeline",
            "endpoint": "http://localhost:9001/mcp",
            "transport": "streamablehttp",
        }
    ]
    config_path = _write_mcp_servers_json(tmp_path, extra)
    servers = load_mcp_servers(config_path)
    clarifeye = next(s for s in servers if s.id == "clarifeye")
    assert str(clarifeye.endpoint) == "http://clarifeye.railway.internal/mcp"


def test_backward_compat_no_auth_field(tmp_path, monkeypatch):
    """Test 11: Existing langchain_rag/llamaindex_rag servers still load with no auth field."""
    monkeypatch.delenv("MCP_LANGCHAIN_RAG_URL", raising=False)
    monkeypatch.delenv("MCP_LLAMAINDEX_RAG_URL", raising=False)

    config_path = _write_mcp_servers_json(tmp_path)
    servers = load_mcp_servers(config_path)
    assert len(servers) == 2
    for s in servers:
        assert s.auth is None
        assert s.sanitize is None


def test_server_with_oauth2_in_json(tmp_path, monkeypatch):
    """Test 12: Server with oauth2 auth block parses correctly from JSON."""
    monkeypatch.delenv("MCP_LANGCHAIN_RAG_URL", raising=False)
    monkeypatch.delenv("MCP_LLAMAINDEX_RAG_URL", raising=False)

    extra = [
        {
            "id": "clarifeye",
            "name": "Clarifeye RAG",
            "description": "Clarifeye RAG pipeline",
            "endpoint": "http://localhost:9001/mcp",
            "transport": "streamablehttp",
            "auth": {
                "type": "oauth2",
                "client_id": "my_client",
                "client_secret_env": "CLARIFEYE_SECRET",
                "token_url": "https://auth.clarifeye.com/token",
            },
            "sanitize": {
                "url_patterns": ["https://clarifeye\\..*"],
                "metadata_keys": ["source_id"],
                "extra_terms": ["Clarifeye"],
            },
        }
    ]
    config_path = _write_mcp_servers_json(tmp_path, extra)
    servers = load_mcp_servers(config_path)
    clarifeye = next(s for s in servers if s.id == "clarifeye")
    assert clarifeye.auth is not None
    assert clarifeye.auth.type == "oauth2"
    assert clarifeye.sanitize is not None
    assert clarifeye.sanitize.extra_terms == ["Clarifeye"]
