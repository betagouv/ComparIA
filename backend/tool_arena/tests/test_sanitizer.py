"""Unit tests for the sanitizer module."""

import pytest

from backend.tool_arena.config import ApiKeyAuth, NoAuth, MCPServerConfig, SanitizeConfig
from backend.tool_arena.normalizer import NormalizedEnvelope, Source
from backend.tool_arena.sanitizer import sanitize_output, sanitize_envelope

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
        auth=NoAuth(type="none"),
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
        auth=ApiKeyAuth(type="api_key", key_env="CLARIFEYE_KEY", header="Authorization"),
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


def test_sanitize_both_servers(server_a, server_b):
    """Test 5: sanitize_output strips identifying info from BOTH servers in the list."""
    text = (
        "Server global_summarizer (Global Summarizer AI) at "
        "https://example.com/mcp/global-summarizer. "
        "Server clarifeye_memos (Clarifeye Memos) at "
        "https://example.com/mcp/clarifeye-memos."
    )
    result = sanitize_output(text, [server_a, server_b])
    assert "global_summarizer" not in result
    assert "Global Summarizer AI" not in result
    assert "https://example.com/mcp/global-summarizer" not in result
    assert "clarifeye_memos" not in result
    assert "Clarifeye Memos" not in result
    assert "https://example.com/mcp/clarifeye-memos" not in result
    assert result.count("[REDACTED]") >= 6


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


# --------------------------------------------------------------------------- #
# sanitize_envelope tests (D-08, D-09)
# --------------------------------------------------------------------------- #

@pytest.fixture
def server_with_sanitize() -> MCPServerConfig:
    return MCPServerConfig(
        id="clarifeye",
        name="Clarifeye RAG",
        description="test",
        endpoint="https://mcp.clarifeye.com/mcp",
        transport="streamablehttp",
        sanitize=SanitizeConfig(
            url_patterns=[r"https://clarifeye\.com/.*"],
            metadata_keys=["doc_id"],
            extra_terms=["Clarifeye", "clarifeye"],
        ),
    )


def test_sanitize_envelope_strips_source_urls(server_with_sanitize):
    """Test: sanitize_envelope sets source url to None (URL stripping D-08)."""
    envelope = NormalizedEnvelope(
        answer="This is the answer.",
        sources=[Source(url="https://clarifeye.com/doc/1", title="Doc 1")],
        confidence=0.9,
        latency_ms=100,
    )
    result = sanitize_envelope(envelope, [server_with_sanitize])
    assert result.sources[0].url is None
    assert result.sources[0].title == "Doc 1"


def test_sanitize_envelope_applies_extra_terms(server_with_sanitize):
    """Test: sanitize_envelope applies per-server extra_terms from SanitizeConfig."""
    envelope = NormalizedEnvelope(
        answer="Clarifeye provides the best RAG results. This is from clarifeye.",
        sources=[],
        confidence=0.8,
        latency_ms=50,
    )
    result = sanitize_envelope(envelope, [server_with_sanitize])
    assert "Clarifeye" not in result.answer
    assert "clarifeye" not in result.answer
    assert "[REDACTED]" in result.answer


def test_sanitize_envelope_applies_url_patterns(server_with_sanitize):
    """Test: sanitize_envelope applies per-server url_patterns regex from SanitizeConfig."""
    envelope = NormalizedEnvelope(
        answer="See https://clarifeye.com/doc/42 for details.",
        sources=[],
        confidence=0.7,
        latency_ms=80,
    )
    result = sanitize_envelope(envelope, [server_with_sanitize])
    assert "https://clarifeye.com/doc/42" not in result.answer
    assert "[REDACTED]" in result.answer


def test_sanitize_envelope_backward_compat_plain_text(server_a, server_b):
    """Test: sanitize_output still works for plain text (backward compat)."""
    text = "The server global_summarizer returned a result."
    result = sanitize_output(text, [server_a, server_b])
    assert "global_summarizer" not in result


def test_sanitize_envelope_no_sanitize_config(server_no_auth):
    """Test: sanitize_envelope with server having no sanitize block still strips source URLs."""
    envelope = NormalizedEnvelope(
        answer="Some answer.",
        sources=[Source(url="https://any.example.com/page", title="Any page")],
        confidence=None,
        latency_ms=0,
    )
    result = sanitize_envelope(envelope, [server_no_auth])
    # Source URLs should be stripped regardless of sanitize config
    assert result.sources[0].url is None
