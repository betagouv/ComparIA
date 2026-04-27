"""Tests for POST /tool-arena/dry-run endpoint (14-02).

Uses a minimal isolated FastAPI test app to avoid psycopg2 imports.
MCP calls are mocked via unittest.mock.AsyncMock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal isolated FastAPI test app (avoids psycopg2/Redis dependency)
# ---------------------------------------------------------------------------

from backend.tool_arena.router import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_server(server_id: str = "test_tool"):
    """Return a minimal MCPServerConfig-like mock."""
    server = MagicMock()
    server.id = server_id
    server.name = "Test RAG Tool"
    server.sanitize = None
    return server


# ---------------------------------------------------------------------------
# Test 1: Happy path — all checks pass, valid=True
# ---------------------------------------------------------------------------

def test_dry_run_happy_path():
    """POST /tool-arena/dry-run with valid tool_id, successful MCP call → valid=True, 3 checks."""
    raw_output = '{"answer": "This document is about testing.", "sources": [], "confidence": 0.9}'

    with patch("backend.tool_arena.router.registry") as mock_registry, \
         patch("backend.tool_arena.router.single_mcp_call", new_callable=AsyncMock) as mock_call:

        mock_registry.get_server.return_value = _make_server("clarifeye")
        mock_call.return_value = (raw_output, 150)

        resp = client.post("/tool-arena/dry-run", json={"tool_id": "clarifeye"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["tool_id"] == "clarifeye"
    assert body["valid"] is True
    assert len(body["checks"]) == 3
    check_names = [c["name"] for c in body["checks"]]
    assert "connectivity" in check_names
    assert "envelope_shape" in check_names
    assert "sanitization" in check_names
    # All checks passed
    for c in body["checks"]:
        assert c["passed"] is True, f"Check {c['name']} unexpectedly failed: {c}"
    # raw_sample should be present
    assert body["raw_sample"] is not None
    assert "answer" in body["raw_sample"]


# ---------------------------------------------------------------------------
# Test 2: Check objects have required schema
# ---------------------------------------------------------------------------

def test_dry_run_check_schema():
    """Each check object must have name, passed, and optional detail."""
    raw_output = "Plain text answer from the tool."

    with patch("backend.tool_arena.router.registry") as mock_registry, \
         patch("backend.tool_arena.router.single_mcp_call", new_callable=AsyncMock) as mock_call:

        mock_registry.get_server.return_value = _make_server("tool_a")
        mock_call.return_value = (raw_output, 100)

        resp = client.post("/tool-arena/dry-run", json={"tool_id": "tool_a"})

    assert resp.status_code == 200
    body = resp.json()
    for check in body["checks"]:
        assert "name" in check
        assert "passed" in check
        assert "detail" in check  # may be None but key must exist


# ---------------------------------------------------------------------------
# Test 3: Unknown tool_id → 404
# ---------------------------------------------------------------------------

def test_dry_run_unknown_tool_id():
    """POST /tool-arena/dry-run with unknown tool_id → 404."""
    with patch("backend.tool_arena.router.registry") as mock_registry:
        mock_registry.get_server.side_effect = KeyError("unknown_tool")
        resp = client.post("/tool-arena/dry-run", json={"tool_id": "unknown_tool"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 4: MCP connectivity failure → connectivity check failed, valid=False
# ---------------------------------------------------------------------------

def test_dry_run_connectivity_failure():
    """When single_mcp_call raises, connectivity check fails and valid=False."""
    with patch("backend.tool_arena.router.registry") as mock_registry, \
         patch("backend.tool_arena.router.single_mcp_call", new_callable=AsyncMock) as mock_call:

        mock_registry.get_server.return_value = _make_server("broken_tool")
        mock_call.side_effect = ConnectionError("MCP server unreachable")

        resp = client.post("/tool-arena/dry-run", json={"tool_id": "broken_tool"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["raw_sample"] is None
    connectivity_check = next(c for c in body["checks"] if c["name"] == "connectivity")
    assert connectivity_check["passed"] is False
    assert connectivity_check["detail"] is not None


# ---------------------------------------------------------------------------
# Test 5: Empty answer → envelope_shape check fails, valid=False
# ---------------------------------------------------------------------------

def test_dry_run_empty_answer_fails_envelope_shape():
    """When MCP call returns empty string, envelope_shape check fails."""
    with patch("backend.tool_arena.router.registry") as mock_registry, \
         patch("backend.tool_arena.router.single_mcp_call", new_callable=AsyncMock) as mock_call:

        mock_registry.get_server.return_value = _make_server("empty_tool")
        mock_call.return_value = ("", 50)  # empty answer

        resp = client.post("/tool-arena/dry-run", json={"tool_id": "empty_tool"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    shape_check = next(c for c in body["checks"] if c["name"] == "envelope_shape")
    assert shape_check["passed"] is False


# ---------------------------------------------------------------------------
# Test 6: Sanitization check always passes, includes detail
# ---------------------------------------------------------------------------

def test_dry_run_sanitization_check_always_passes():
    """Sanitization check is always passed (best-effort), detail shows field count."""
    raw_output = '{"answer": "Result from clarifeye endpoint https://clarifeye.example.com", "sources": [{"url": "https://clarifeye.example.com/doc1"}]}'

    with patch("backend.tool_arena.router.registry") as mock_registry, \
         patch("backend.tool_arena.router.single_mcp_call", new_callable=AsyncMock) as mock_call:

        mock_registry.get_server.return_value = _make_server("clarifeye")
        mock_call.return_value = (raw_output, 200)

        resp = client.post("/tool-arena/dry-run", json={"tool_id": "clarifeye"})

    assert resp.status_code == 200
    body = resp.json()
    sanitization_check = next(c for c in body["checks"] if c["name"] == "sanitization")
    assert sanitization_check["passed"] is True
