"""Unit tests for env var URL overlay in load_mcp_servers()."""

import json
import os
import pytest
from pathlib import Path

from backend.tool_arena.config import load_mcp_servers


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _write_mcp_servers_json(tmp_path: Path) -> Path:
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
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(json.dumps(data))
    return config_path


# --------------------------------------------------------------------------- #
# Tests
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
