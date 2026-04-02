"""
MCPRegistry — singleton registry of MCP servers loaded from mcp_servers.json.

Provides server selection (pick_two) and lookup (get_server) for the Tool Arena.
Self-contained module — does NOT import from backend.arena.
"""

import random

from backend.tool_arena.config import MCPServerConfig, load_mcp_servers


class MCPRegistry:
    """
    Singleton registry of MCP servers loaded from mcp_servers.json.

    Instantiated at module level so config errors propagate at import time
    before FastAPI accepts any requests (per D-07).
    """

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        self._servers: dict[str, MCPServerConfig] = {s.id: s for s in servers}

    def pick_two(self) -> tuple[MCPServerConfig, MCPServerConfig]:
        """
        Return two randomly selected server configs (per D-08).

        - If exactly 2 servers: always returns that pair (per D-09)
        - If >2 servers: random.sample without replacement (per D-09)
        - If <2 servers: impossible — blocked by load_mcp_servers validation (per D-07)
        """
        servers = list(self._servers.values())
        a, b = random.sample(servers, 2)
        return a, b

    def get_server(self, server_id: str) -> MCPServerConfig:
        """
        Look up a server config by ID (per D-10).

        Used in Phase 3 for reveal lookups after voting.
        Raises KeyError if server_id not found.
        """
        return self._servers[server_id]

    @property
    def server_ids(self) -> list[str]:
        """List all registered server IDs."""
        return list(self._servers.keys())

    def __len__(self) -> int:
        return len(self._servers)


# Module-level singleton — raises at import time if config is invalid (per D-08)
# Mirrors: settings = Settings() pattern in backend/config.py
registry = MCPRegistry(load_mcp_servers())
