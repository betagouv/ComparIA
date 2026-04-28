"""OAuth2 authorization_code auth for MCP servers via the MCP SDK.

Uses the MCP SDK's OAuthClientProvider which handles:
- Authorization code flow with PKCE (S256)
- Token storage and automatic refresh via refresh_token
- 401 retry with re-authentication

Token storage strategy:
- Production (Redis available): RedisTokenStorage — persists across Railway deploys
- Local dev (no Redis): FileTokenStorage — writes to .oauth_tokens/ on disk
- Bootstrap: if {SERVER_ID}_REFRESH_TOKEN env var exists and no stored tokens,
  seeds the initial refresh_token so the SDK can refresh without browser auth

One-time setup: run `uv run python -m scripts.auth_setup <tool_id>` locally
to obtain tokens via browser auth. The refresh_token persists in Redis.
"""

import json
import logging
import os
from pathlib import Path

import httpx
from mcp.client.auth import OAuthClientProvider
from mcp.client.auth.exceptions import OAuthTokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from backend.tool_arena.config import MCPServerConfig, OAuth2Auth

logger = logging.getLogger("tool_arena.auth")

TOKENS_DIR = Path(__file__).parent.parent.parent / ".oauth_tokens"

REDIS_TOKEN_KEY = "oauth_tokens:{server_id}"
REDIS_CLIENT_INFO_KEY = "oauth_client_info:{server_id}"


class RedisTokenStorage:
    """Stores OAuth tokens and client info in Redis — survives Railway redeploys."""

    def __init__(self, server_id: str, redis_client) -> None:
        self._server_id = server_id
        self._redis = redis_client

    async def get_tokens(self) -> OAuthToken | None:
        data = self._redis.get(REDIS_TOKEN_KEY.format(server_id=self._server_id))
        if not data:
            return None
        return OAuthToken(**json.loads(data))

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._redis.set(
            REDIS_TOKEN_KEY.format(server_id=self._server_id),
            tokens.model_dump_json(),
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        data = self._redis.get(REDIS_CLIENT_INFO_KEY.format(server_id=self._server_id))
        if not data:
            return None
        return OAuthClientInformationFull(**json.loads(data))

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._redis.set(
            REDIS_CLIENT_INFO_KEY.format(server_id=self._server_id),
            client_info.model_dump_json(),
        )


class FileTokenStorage:
    """Stores OAuth tokens and client info as JSON files on disk (local dev fallback)."""

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


def _get_storage(server_id: str) -> RedisTokenStorage | FileTokenStorage:
    """Get token storage: Redis if available, file fallback for local dev."""
    try:
        from utils.storage.redis import get_redis_client
        client = get_redis_client()
        client.ping()
        logger.debug("Using Redis token storage for %s", server_id)
        return RedisTokenStorage(server_id, client)
    except Exception:
        logger.debug("Redis unavailable, using file token storage for %s", server_id)
        return FileTokenStorage(server_id)


def _bootstrap_tokens_from_env(server: MCPServerConfig, storage) -> None:
    """Pre-seed tokens from env var if no tokens exist in storage.

    Looks for {SERVER_ID}_REFRESH_TOKEN env var (e.g. CLARIFEYE_REFRESH_TOKEN).
    Seeds the storage with an expired access_token + the refresh_token so the
    SDK refreshes automatically on first request.
    """
    env_key = f"{server.id.upper()}_REFRESH_TOKEN"
    refresh_token = os.environ.get(env_key, "")
    if not refresh_token:
        return

    # Check if tokens already exist (sync — called before event loop starts)
    if isinstance(storage, FileTokenStorage):
        if (storage._dir / "tokens.json").exists():
            return
    elif isinstance(storage, RedisTokenStorage):
        if storage._redis.get(REDIS_TOKEN_KEY.format(server_id=server.id)):
            return

    bootstrap = OAuthToken(
        access_token="",
        token_type="Bearer",
        refresh_token=refresh_token,
    )

    if isinstance(storage, FileTokenStorage):
        (storage._dir / "tokens.json").write_text(bootstrap.model_dump_json(indent=2))
    elif isinstance(storage, RedisTokenStorage):
        storage._redis.set(
            REDIS_TOKEN_KEY.format(server_id=server.id),
            bootstrap.model_dump_json(),
        )

    logger.info("Bootstrapped OAuth tokens for %s from %s env var", server.id, env_key)


class CompaRAGOAuthProvider(OAuthClientProvider):
    """OAuthClientProvider that overrides _refresh_token() to use configured token_url.

    The SDK's _refresh_token() falls back to {server_url}/token before OAuth metadata
    is discovered. For Clarifeye the endpoint is /o/token/. This override uses the
    token_url from mcp_servers.json so refresh works on the very first request.
    """

    def __init__(self, token_url: str, **kwargs):
        super().__init__(**kwargs)
        self._configured_token_url = token_url

    async def _refresh_token(self) -> httpx.Request:
        if not self.context.current_tokens or not self.context.current_tokens.refresh_token:
            raise OAuthTokenError("No refresh token available")
        if not self.context.client_info or not self.context.client_info.client_id:
            raise OAuthTokenError("No client info available")

        if self.context.oauth_metadata and self.context.oauth_metadata.token_endpoint:
            token_url = str(self.context.oauth_metadata.token_endpoint)
        else:
            token_url = self._configured_token_url

        refresh_data: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": self.context.current_tokens.refresh_token,
            "client_id": self.context.client_info.client_id,
        }

        if self.context.should_include_resource_param(self.context.protocol_version):
            refresh_data["resource"] = self.context.get_resource_url()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        refresh_data, headers = self.context.prepare_token_auth(refresh_data, headers)

        return httpx.Request("POST", token_url, data=refresh_data, headers=headers)


async def _redirect_handler(url: str) -> None:
    """Redirect handler for auth code flow — should never be called in production."""
    raise RuntimeError(
        f"OAuth authorization_code flow triggered on headless server. "
        f"Run 'uv run python -m scripts.auth_setup <tool_id>' locally to obtain tokens. "
        f"Auth URL: {url}"
    )


async def _callback_handler() -> tuple[str, str | None]:
    """Callback handler — should never be called in production."""
    raise RuntimeError("OAuth callback triggered on headless server — this should not happen.")


def build_oauth_provider(server: MCPServerConfig) -> CompaRAGOAuthProvider:
    """Build an OAuthClientProvider for an OAuth2-authenticated MCP server.

    Token storage: Redis in production, file on disk for local dev.
    Initial tokens bootstrapped from env var or obtained via auth_setup.py.
    """
    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")

    storage = _get_storage(server.id)

    # Bootstrap refresh token from env var if no tokens in storage
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
    if isinstance(storage, FileTokenStorage):
        p = storage._dir / "client_info.json"
        p.write_text(client_info.model_dump_json(indent=2))
    elif isinstance(storage, RedisTokenStorage):
        storage._redis.set(
            REDIS_CLIENT_INFO_KEY.format(server_id=server.id),
            client_info.model_dump_json(),
        )

    return CompaRAGOAuthProvider(
        token_url=auth.token_url,
        server_url=str(server.endpoint),
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
    )


_provider_cache: dict[str, CompaRAGOAuthProvider] = {}


def get_oauth_provider(server: MCPServerConfig) -> CompaRAGOAuthProvider:
    """Get or create a cached CompaRAGOAuthProvider for the server."""
    if server.id not in _provider_cache:
        _provider_cache[server.id] = build_oauth_provider(server)
    return _provider_cache[server.id]


def _clear_token_cache() -> None:
    """Clear provider cache. Used for test isolation."""
    _provider_cache.clear()
