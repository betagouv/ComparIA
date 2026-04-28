"""OAuth2 authorization_code auth for MCP servers via the MCP SDK.

Uses the MCP SDK's OAuthClientProvider which handles:
- Authorization code flow with PKCE (S256)
- Token storage and automatic refresh via refresh_token
- 401 retry with re-authentication

For servers requiring OAuth2, a one-time local setup (scripts/auth_setup.py)
obtains tokens. The refresh_token is stored as an env var on Railway. The
provider loads it at startup and refreshes automatically.
"""

import json
import logging
import os
from pathlib import Path

from mcp.client.auth import OAuthClientProvider
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


def _bootstrap_tokens_from_env(server: MCPServerConfig, storage: FileTokenStorage) -> None:
    """Pre-seed tokens from env var so OAuthClientProvider can refresh without browser auth.

    Looks for {SERVER_ID}_REFRESH_TOKEN env var (e.g. CLARIFEYE_REFRESH_TOKEN).
    If found and no tokens on disk, writes a bootstrap tokens.json with the refresh_token.
    The SDK will use it to obtain a fresh access_token on first request.
    """
    env_key = f"{server.id.upper()}_REFRESH_TOKEN"
    refresh_token = os.environ.get(env_key, "")
    if not refresh_token:
        return

    tokens_path = storage._dir / "tokens.json"
    if tokens_path.exists():
        return

    bootstrap = OAuthToken(
        access_token="expired",
        token_type="Bearer",
        refresh_token=refresh_token,
    )
    tokens_path.write_text(bootstrap.model_dump_json(indent=2))
    logger.info("Bootstrapped OAuth tokens for %s from %s env var", server.id, env_key)


async def _redirect_handler(url: str) -> None:
    """Redirect handler for auth code flow — should never be called in production."""
    raise RuntimeError(
        f"OAuth authorization_code flow triggered on headless server. "
        f"Run 'python scripts/auth_setup.py' locally to obtain tokens, then set "
        f"the refresh token as an env var. Auth URL: {url}"
    )


async def _callback_handler() -> tuple[str, str | None]:
    """Callback handler — should never be called in production."""
    raise RuntimeError("OAuth callback triggered on headless server — this should not happen.")


def build_oauth_provider(server: MCPServerConfig) -> OAuthClientProvider:
    """Build an OAuthClientProvider for an OAuth2-authenticated MCP server.

    The provider handles token refresh and 401 re-auth automatically.
    Initial tokens must be bootstrapped from env var or obtained via auth_setup.py.
    """
    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")

    storage = FileTokenStorage(server.id)

    # Bootstrap refresh token from env var if no tokens on disk
    _bootstrap_tokens_from_env(server, storage)

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
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
    )


_provider_cache: dict[str, OAuthClientProvider] = {}


def get_oauth_provider(server: MCPServerConfig) -> OAuthClientProvider:
    """Get or create a cached OAuthClientProvider for the server."""
    if server.id not in _provider_cache:
        _provider_cache[server.id] = build_oauth_provider(server)
    return _provider_cache[server.id]


def _clear_token_cache() -> None:
    """Clear provider cache. Used for test isolation."""
    _provider_cache.clear()
