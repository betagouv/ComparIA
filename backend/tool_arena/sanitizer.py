"""Identity sanitization for CompaRAG Tool Arena.

Strips MCP server identifying information (id, name, endpoint, auth token)
from text to prevent identity leakage before blind voting.
"""

import re

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
        if server.auth and server.auth.token:
            patterns.append(re.escape(server.auth.token))

    if not patterns:
        return text

    combined = "|".join(patterns)
    return re.sub(combined, "[REDACTED]", text, flags=re.IGNORECASE)
