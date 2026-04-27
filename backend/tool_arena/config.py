"""
MCP server configuration for CompaRAG Tool Arena.

Defines validated Pydantic models for MCP server entries and provides
a loader function that validates the mcp_servers.json config file.

Self-contained module — does NOT import from backend.arena or backend.config.
"""

import json
import os
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, PlainSerializer


# Path to mcp_servers.json relative to the CompaRAG project root
# backend/tool_arena/ -> CompaRAG/
ROOT_DIR = Path(__file__).parent.parent.parent
MCP_SERVERS_PATH = ROOT_DIR / "mcp_servers.json"


# --------------------------------------------------------------------------- #
# Auth union (D-01): polymorphic discriminated union on `type`
# --------------------------------------------------------------------------- #

class OAuth2Auth(BaseModel):
    """OAuth2 client_credentials auth. Secrets stored as env var names, never literals."""

    type: Literal["oauth2"]
    client_id: str
    client_secret_env: str  # env var name, not literal secret
    token_url: str


class ApiKeyAuth(BaseModel):
    """API key auth. Key stored as env var name, not literal value."""

    type: Literal["api_key"]
    key_env: str  # env var name
    header: str = "Authorization"


class NoAuth(BaseModel):
    """No authentication required."""

    type: Literal["none"]


MCPAuthConfig = Annotated[
    OAuth2Auth | ApiKeyAuth | NoAuth,
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Per-server sanitize block (D-02)
# --------------------------------------------------------------------------- #

class SanitizeConfig(BaseModel):
    """Per-server sanitization configuration.

    url_patterns: Regex patterns to strip from answer text (source URLs, vendor domains).
    metadata_keys: JSON keys to strip from structured output.
    extra_terms: Additional literal terms to redact from answer text.
    """

    url_patterns: list[str] = []
    metadata_keys: list[str] = []
    extra_terms: list[str] = []


# --------------------------------------------------------------------------- #
# Main server config
# --------------------------------------------------------------------------- #

class MCPServerConfig(BaseModel):
    """
    Configuration for a single MCP server entry.

    Each server represents a tool contestant in the arena.
    """

    id: str  # server identifier key (matches mcp_servers.json top-level key)
    name: str  # display name shown in reveal UI after voting
    description: str  # short text shown in arena UI
    endpoint: Annotated[HttpUrl, PlainSerializer(str)]  # URL with str serialization
    transport: Literal["streamablehttp"]  # only valid transport (SSE deprecated per MCP spec v2025-03-26)
    auth: MCPAuthConfig | None = None
    sanitize: SanitizeConfig | None = None
    tools: list[str] = ["*"]  # which MCP tools to call; ["*"] means all
    tool_args: dict[str, str] = {}  # extra static args merged into every tool call


def load_mcp_servers(path: Path | None = None) -> list[MCPServerConfig]:
    """
    Load and validate MCP server configurations from a JSON file.

    Args:
        path: Path to the JSON config file. Defaults to MCP_SERVERS_PATH
              (CompaRAG/mcp_servers.json).

    Returns:
        list[MCPServerConfig]: Validated list of at least 2 server configs.

    Raises:
        FileNotFoundError: If the config file does not exist.
        json.JSONDecodeError: If the file contains malformed JSON.
        pydantic.ValidationError: If any server entry fails field validation.
        ValueError: If fewer than 2 servers are defined.
    """
    if path is None:
        path = MCP_SERVERS_PATH

    if not path.exists():
        raise FileNotFoundError(f"MCP server config not found at {path}")

    with open(path) as f:
        raw = json.load(f)  # raises json.JSONDecodeError on malformed JSON

    # D-03: Convention-based URL override — derived from server id.
    # e.g. id="clarifeye" -> env var "MCP_CLARIFEYE_URL"
    # Backward compatible: "langchain_rag" -> MCP_LANGCHAIN_RAG_URL (same as before)
    for entry in raw:
        server_id = entry.get("id", "")
        env_var = f"MCP_{server_id.upper()}_URL"
        override_url = os.getenv(env_var)
        if override_url:
            entry["endpoint"] = override_url

    servers = [MCPServerConfig(**entry) for entry in raw]  # raises ValidationError on invalid fields

    if len(servers) < 2:
        raise ValueError(
            f"mcp_servers.json must define at least 2 servers, found {len(servers)}"
        )

    return servers
