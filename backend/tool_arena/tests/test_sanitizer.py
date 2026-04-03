"""Unit tests for the sanitizer module."""

import pytest

from backend.tool_arena.config import MCPAuth, MCPServerConfig
from backend.tool_arena.sanitizer import sanitize_output

# --------------------------------------------------------------------------- #
# Test fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def server_a() -> MCPServerConfig:
    return MCPServerConfig(
        id="global_summarizer",
        name="Global Summarizer AI",
        description="test",
        endpoint="https://example.com/mcp/global-summarizer",
        transport="streamablehttp",
        auth=MCPAuth(type="bearer", token="secret_token_abc"),
        tools=["*"],
    )


@pytest.fixture
def server_b() -> MCPServerConfig:
    return MCPServerConfig(
        id="clarifeye_memos",
        name="Clarifeye Memos",
        description="test",
        endpoint="https://example.com/mcp/clarifeye-memos",
        transport="streamablehttp",
        auth=MCPAuth(type="bearer", token="secret_token_xyz"),
        tools=["extract_memo"],
    )


@pytest.fixture
def server_no_auth() -> MCPServerConfig:
    return MCPServerConfig(
        id="open_server",
        name="Open Server",
        description="test",
        endpoint="https://example.com/mcp/open",
        transport="streamablehttp",
        auth=None,
        tools=["*"],
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_sanitize_replaces_server_id(server_a, server_b):
    """Test 1: sanitize_output replaces server id 'global_summarizer' with '[REDACTED]'."""
    text = "The server global_summarizer returned this response."
    result = sanitize_output(text, [server_a, server_b])
    assert "[REDACTED]" in result
    assert "global_summarizer" not in result


def test_sanitize_replaces_server_name_case_insensitive(server_a, server_b):
    """Test 2: sanitize_output replaces server name case-insensitively."""
    text = "Response from Global Summarizer AI about something."
    result = sanitize_output(text, [server_a, server_b])
    assert "[REDACTED]" in result
    assert "Global Summarizer AI" not in result
    assert "global summarizer ai" not in result.lower()


def test_sanitize_replaces_endpoint_url(server_a, server_b):
    """Test 3: sanitize_output replaces server endpoint URL with '[REDACTED]'."""
    text = "Connecting to https://example.com/mcp/global-summarizer for the task."
    result = sanitize_output(text, [server_a, server_b])
    assert "[REDACTED]" in result
    assert "https://example.com/mcp/global-summarizer" not in result


def test_sanitize_replaces_auth_token(server_a, server_b):
    """Test 4: sanitize_output replaces auth token with '[REDACTED]'."""
    text = "Using token secret_token_abc for authorization."
    result = sanitize_output(text, [server_a, server_b])
    assert "[REDACTED]" in result
    assert "secret_token_abc" not in result


def test_sanitize_both_servers(server_a, server_b):
    """Test 5: sanitize_output strips identifying info from BOTH servers in the list."""
    text = (
        "Server global_summarizer (Global Summarizer AI) at "
        "https://example.com/mcp/global-summarizer used token secret_token_abc. "
        "Server clarifeye_memos (Clarifeye Memos) at "
        "https://example.com/mcp/clarifeye-memos used token secret_token_xyz."
    )
    result = sanitize_output(text, [server_a, server_b])
    assert "global_summarizer" not in result
    assert "Global Summarizer AI" not in result
    assert "https://example.com/mcp/global-summarizer" not in result
    assert "secret_token_abc" not in result
    assert "clarifeye_memos" not in result
    assert "Clarifeye Memos" not in result
    assert "https://example.com/mcp/clarifeye-memos" not in result
    assert "secret_token_xyz" not in result
    assert result.count("[REDACTED]") >= 8


def test_sanitize_no_match_returns_original(server_a, server_b):
    """Test 6: sanitize_output returns original text unchanged when no patterns match."""
    text = "This text contains no server-identifying information."
    result = sanitize_output(text, [server_a, server_b])
    assert result == text


def test_sanitize_empty_string(server_a, server_b):
    """Test 7: sanitize_output returns empty string when given empty string."""
    result = sanitize_output("", [server_a, server_b])
    assert result == ""


def test_sanitize_empty_servers_list(server_a):
    """Test 8: sanitize_output returns original text when servers list is empty."""
    text = "Some text with global_summarizer in it."
    result = sanitize_output(text, [])
    assert result == text


def test_sanitize_server_with_no_auth(server_no_auth):
    """Test 9: sanitize_output handles server with auth=None (no token to strip)."""
    text = "Connecting to open_server at https://example.com/mcp/open."
    result = sanitize_output(text, [server_no_auth])
    assert "open_server" not in result
    assert "[REDACTED]" in result
