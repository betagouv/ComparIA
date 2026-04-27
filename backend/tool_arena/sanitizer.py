"""Identity sanitization for CompaRAG Tool Arena.

Strips MCP server identifying information (id, name, endpoint, auth token)
from text to prevent identity leakage before blind voting.

Extended in Phase 14 to support:
- sanitize_envelope(): operates on NormalizedEnvelope, strips source URLs (D-08)
  and applies per-server sanitize config (D-09)
"""

import re
import copy

from backend.tool_arena.config import MCPServerConfig


def sanitize_output(text: str, servers: list[MCPServerConfig]) -> str:
    """Strip server identifying information from text.

    Builds regex patterns dynamically from MCPServerConfig fields at runtime.
    Replaces matches with '[REDACTED]' using case-insensitive matching.

    Args:
        text: The text to sanitize (raw MCP output or LLM mediated result).
        servers: List of MCPServerConfig objects whose identifying fields
                 should be stripped from the text.

    Returns:
        Sanitized text with all server-identifying strings replaced.
    """
    if not text or not servers:
        return text

    patterns: list[str] = []
    for server in servers:
        for value in [server.id, server.name, str(server.endpoint)]:
            if value:
                patterns.append(re.escape(value))
        # New auth types (OAuth2Auth, ApiKeyAuth, NoAuth) store env var names, not literals.
        # No literal secrets to redact from auth config in the new design.

    if not patterns:
        return text

    combined = "|".join(patterns)
    return re.sub(combined, "[REDACTED]", text, flags=re.IGNORECASE)


def sanitize_envelope(envelope, servers: list[MCPServerConfig]):
    """Sanitize a NormalizedEnvelope before blind display.

    Actions per D-08/D-09:
    1. Strip source URLs: set each source.url to None (preserved internally
       for Phase 17 citation reveal — no leakage risk).
    2. Apply per-server sanitize.extra_terms as regex patterns to answer text.
    3. Apply per-server sanitize.url_patterns as regex patterns to answer text.

    Existing id/name/endpoint stripping from sanitize_output() is NOT duplicated
    here — dispatcher calls sanitize_output() on raw text first, then
    sanitize_envelope() on the normalized envelope.

    Args:
        envelope: NormalizedEnvelope to sanitize (imported at call site to avoid
                  circular imports — normalizer imports nothing from sanitizer).
        servers: List of MCPServerConfig objects to read sanitize config from.

    Returns:
        New NormalizedEnvelope with source URLs stripped and answer text cleaned.
    """
    # Deep copy to avoid mutating the original
    sanitized_sources = []
    for source in envelope.sources:
        sanitized_sources.append(source.model_copy(update={"url": None}))

    # Build answer text patterns from per-server sanitize config
    answer = envelope.answer
    answer_patterns: list[str] = []

    for server in servers:
        if server.sanitize:
            for term in server.sanitize.extra_terms:
                if term:
                    answer_patterns.append(re.escape(term))
            for pattern in server.sanitize.url_patterns:
                if pattern:
                    answer_patterns.append(pattern)

    if answer_patterns:
        combined = "|".join(answer_patterns)
        answer = re.sub(combined, "[REDACTED]", answer, flags=re.IGNORECASE)

    return envelope.model_copy(update={
        "sources": sanitized_sources,
        "answer": answer,
    })
