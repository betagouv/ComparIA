"""OAuth2 authorization_code + PKCE auth for MCP servers via the MCP SDK.

Uses the MCP SDK's OAuthClientProvider which handles:
- Authorization code flow with PKCE (S256)
- Token storage and automatic refresh
- 401 retry with re-authentication

For servers requiring OAuth2, a one-time browser-based login stores tokens
to disk. The backend then uses refresh tokens automatically.
"""

import json
import logging
import os
from pathlib import Path

from mcp.client.auth import OAuthClientProvider
from mcp.client.auth import TokenStorage as TokenStorageProtocol
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

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


def build_oauth_provider(server: MCPServerConfig) -> OAuthClientProvider:
    """Build an OAuthClientProvider for an OAuth2-authenticated MCP server.

    The provider is passed as auth= to streamablehttp_client. It handles
    token refresh and 401 re-auth automatically.
    """
    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")

    storage = FileTokenStorage(server.id)

    client_info = OAuthClientInformationFull(
        client_id=auth.client_id,
        client_secret=client_secret or None,
        redirect_uris=["http://localhost:9876/callback"],
    )

    client_metadata = OAuthClientMetadata(
        redirect_uris=["http://localhost:9876/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        client_name="CompaRAG Tool Arena",
        scope="claudeai openid offline_access",
        token_endpoint_auth_method="client_secret_post",
    )

    # Pre-seed client info so the SDK doesn't try dynamic registration
    p = storage._dir / "client_info.json"
    p.write_text(client_info.model_dump_json(indent=2))

    return OAuthClientProvider(
        server_url=str(server.endpoint),
        client_metadata=client_metadata,
        storage=storage,
    )


# Cache providers by server_id to reuse token state
_provider_cache: dict[str, OAuthClientProvider] = {}


def get_oauth_provider(server: MCPServerConfig) -> OAuthClientProvider:
    """Get or create a cached OAuthClientProvider for the server."""
    if server.id not in _provider_cache:
        _provider_cache[server.id] = build_oauth_provider(server)
    return _provider_cache[server.id]


def _clear_token_cache() -> None:
    """Clear provider cache. Used for test isolation."""
    _provider_cache.clear()
