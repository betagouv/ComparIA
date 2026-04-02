"""
MCP server configuration for CompaRAG Tool Arena.

Defines validated Pydantic models for MCP server entries and provides
a loader function that validates the mcp_servers.json config file.

Self-contained module — does NOT import from backend.arena or backend.config.
"""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, HttpUrl, PlainSerializer

# Path to mcp_servers.json relative to the CompaRAG project root
# backend/tool_arena/ -> CompaRAG/
ROOT_DIR = Path(__file__).parent.parent.parent
MCP_SERVERS_PATH = ROOT_DIR / "mcp_servers.json"


class MCPAuth(BaseModel):
    """Authentication credentials for an MCP server."""

    type: str  # e.g., "bearer"
    token: str | None = None
    header: str | None = None


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
    auth: MCPAuth | None = None
    tools: list[str] = ["*"]  # which MCP tools to call; ["*"] means all


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

    servers = [MCPServerConfig(**entry) for entry in raw]  # raises ValidationError on invalid fields

    if len(servers) < 2:
        raise ValueError(
            f"mcp_servers.json must define at least 2 servers, found {len(servers)}"
        )

    return servers
