"""OAuth2 client_credentials auth for MCP servers.

Uses the MCP SDK's ClientCredentialsOAuthProvider which handles:
- client_credentials grant (no browser redirect needed)
- Token storage and automatic refresh
- 401 retry with re-authentication
"""

import json
import logging
import os
from pathlib import Path

from mcp.client.auth.extensions.client_credentials import ClientCredentialsOAuthProvider
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from backend.tool_arena.config import MCPServerConfig, OAuth2Auth

logger = logging.getLogger("tool_arena.auth")

TOKENS_DIR = Path(__file__).parent.parent.parent / ".oauth_tokens"


class FileTokenStorage:
    """Stores OAuth tokens and client info as JSON files on disk."""

    def __init__(self, server_id: str) -> None:
        self._dir = TOKENS_DIR / server_id
        self._dir.mkdir(parents=True, exist_ok=True)

    async def get_tokens(self) -> OAuthToken | None:
        p = self._dir / "tokens.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        return OAuthToken(**data)

    async def set_tokens(self, tokens: OAuthToken) -> None:
        p = self._dir / "tokens.json"
        p.write_text(tokens.model_dump_json(indent=2))

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        p = self._dir / "client_info.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        return OAuthClientInformationFull(**data)

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        p = self._dir / "client_info.json"
        p.write_text(client_info.model_dump_json(indent=2))


def build_oauth_provider(server: MCPServerConfig) -> ClientCredentialsOAuthProvider:
    """Build a ClientCredentialsOAuthProvider for an OAuth2-authenticated MCP server."""
    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")
    storage = FileTokenStorage(server.id)

    return ClientCredentialsOAuthProvider(
        server_url=str(server.endpoint),
        storage=storage,
        client_id=auth.client_id,
        client_secret=client_secret,
        token_endpoint_auth_method="client_secret_post",
    )


_provider_cache: dict[str, ClientCredentialsOAuthProvider] = {}


def get_oauth_provider(server: MCPServerConfig) -> ClientCredentialsOAuthProvider:
    """Get or create a cached ClientCredentialsOAuthProvider for the server."""
    if server.id not in _provider_cache:
        _provider_cache[server.id] = build_oauth_provider(server)
    return _provider_cache[server.id]


def _clear_token_cache() -> None:
    """Clear provider cache. Used for test isolation."""
    _provider_cache.clear()
