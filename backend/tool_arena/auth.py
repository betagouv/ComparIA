"""OAuth2 authorization_code auth for MCP servers via the MCP SDK.

Uses the MCP SDK's OAuthClientProvider which handles:
- Authorization code flow with PKCE (S256)
- Token storage and automatic refresh via refresh_token
- 401 retry with re-authentication

Token storage strategy:
- Production (Redis available): RedisTokenStorage — persists across Railway deploys
- Local dev (no Redis): FileTokenStorage — writes to .oauth_tokens/ on disk

Tokens are seeded via ``POST /admin/tool-arena/oauth/seed`` after running
``scripts/auth_setup.py`` locally. There is no env-var bootstrap: the prior
``{SERVER_ID}_REFRESH_TOKEN`` env-var path was removed because it silently
re-seeded a revoked (rotated) refresh_token whenever Redis was wiped.

A Redis distributed lock (``oauth_refresh_lock:{server_id}``) is held for the
duration of a token refresh so multi-replica deployments cannot clobber each
other when refresh_token rotation is enabled upstream.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx
from mcp.client.auth import OAuthClientProvider
from mcp.client.auth.exceptions import OAuthTokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from backend.tool_arena.config import MCPServerConfig, OAuth2Auth

logger = logging.getLogger("languia")

TOKENS_DIR = Path(__file__).parent.parent.parent / ".oauth_tokens"

REDIS_TOKEN_KEY = "oauth_tokens:{server_id}"
REDIS_CLIENT_INFO_KEY = "oauth_client_info:{server_id}"

# Per-server timeout for the startup OAuth pre-warm handshake.
PREWARM_TIMEOUT_SECONDS = float(os.environ.get("OAUTH_PREWARM_TIMEOUT", "20"))


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


REDIS_REFRESH_LOCK_KEY = "oauth_refresh_lock:{server_id}"
REFRESH_LOCK_TTL_MS = 30_000  # 30s — refresh usually <2s; generous for slow IdPs.


async def _with_refresh_lock(
    server_id: str,
    storage: "RedisTokenStorage | FileTokenStorage",
    do_refresh,
):
    """Run ``do_refresh()`` while holding a Redis distributed lock.

    Prevents two replicas from refreshing the same OAuth refresh_token
    concurrently. Clarifeye rotates refresh_tokens on every refresh — without
    a lock, the loser of the race holds a revoked token.

    Strategy:
      * Try ``SET NX PX`` to acquire ``oauth_refresh_lock:{server_id}``.
      * If acquired, run ``do_refresh()`` and release the key in ``finally``.
      * If not acquired, sleep with exponential backoff (200/400/800/1600/3200
        ms, max 5 attempts). After each sleep, re-check storage: if a fresh
        token appeared, return ``None`` and let the caller use it instead of
        re-refreshing.
      * If we exhaust attempts, fall through and run ``do_refresh()`` anyway —
        better to risk a clobber than to deadlock the request indefinitely.

    For ``FileTokenStorage`` (single-process dev) the lock is a no-op.
    """
    if not isinstance(storage, RedisTokenStorage):
        return await do_refresh()

    redis_client = storage._redis
    lock_key = REDIS_REFRESH_LOCK_KEY.format(server_id=server_id)
    lock_value = f"{os.getpid()}:{asyncio.get_event_loop().time()}"

    acquired = False
    try:
        acquired = bool(
            redis_client.set(lock_key, lock_value, nx=True, px=REFRESH_LOCK_TTL_MS)
        )
        if acquired:
            return await do_refresh()

        # Wait for the holder; check storage between sleeps so we can short-
        # circuit when a fresh token appears.
        backoff_ms = 200
        for _ in range(5):
            await asyncio.sleep(backoff_ms / 1000.0)
            existing = await storage.get_tokens()
            if existing is not None and existing.access_token and existing.access_token not in (
                "",
                "bootstrap-pending-refresh",
            ):
                logger.debug(
                    "Refresh lock waiter for %s saw a fresh token; skipping refresh",
                    server_id,
                )
                return None
            backoff_ms = min(backoff_ms * 2, 3200)

        # Last resort: take the lock by force and refresh anyway.
        logger.warning(
            "Refresh lock for %s held by another holder beyond backoff window; "
            "proceeding without lock",
            server_id,
        )
        return await do_refresh()
    finally:
        if acquired:
            try:
                # Best-effort release; the TTL covers crashes.
                stored = redis_client.get(lock_key)
                if stored == lock_value:
                    redis_client.delete(lock_key)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Refresh lock release for %s failed: %s", server_id, exc)


class CompaRAGOAuthProvider(OAuthClientProvider):
    """OAuthClientProvider that overrides _refresh_token() to use configured token_url.

    The SDK's _refresh_token() falls back to {server_url}/token before OAuth metadata
    is discovered. For Clarifeye the endpoint is /o/token/. This override uses the
    token_url from mcp_servers.json so refresh works on the very first request.
    """

    def __init__(self, token_url: str, server_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._configured_token_url = token_url
        # Stored so the lock helper can scope to this server. Optional so
        # existing tests that build the provider directly continue to work.
        self._server_id = server_id

    async def _build_refresh_request(self) -> httpx.Request:
        """Original refresh request builder — extracted so the lock can wrap it."""
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

    async def _refresh_token(self) -> httpx.Request:
        """Wrap the SDK refresh in a Redis distributed lock to avoid clobber.

        We override the SDK's seam (rather than guarding the wider
        ``async_auth_flow``) because this is the narrowest place where rotation
        actually matters. If a peer replica refreshed while we were waiting,
        the storage already has fresh tokens — but the SDK still needs a
        valid ``httpx.Request`` from this method to drive the next call. We
        therefore always build the request, but the lock ensures that only
        one replica is mid-flight against the IdP at a time.
        """
        if self._server_id is None:
            return await self._build_refresh_request()

        storage = self.context.storage  # set by SDK on init
        if not isinstance(storage, (RedisTokenStorage, FileTokenStorage)):
            return await self._build_refresh_request()

        result = await _with_refresh_lock(
            self._server_id,
            storage,
            self._build_refresh_request,
        )
        if result is None:
            # A peer replica already refreshed; reuse its result by issuing the
            # same request shape — the SDK's downstream flow will see the new
            # access_token in storage on the next get_tokens() call.
            return await self._build_refresh_request()
        return result


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


def _read_stored_client_info(
    storage: RedisTokenStorage | FileTokenStorage,
    server_id: str,
) -> OAuthClientInformationFull | None:
    """Synchronously read stored client_info, if any. Returns None on any error."""
    try:
        if isinstance(storage, FileTokenStorage):
            p = storage._dir / "client_info.json"
            if not p.exists():
                return None
            return OAuthClientInformationFull(**json.loads(p.read_text()))
        if isinstance(storage, RedisTokenStorage):
            raw = storage._redis.get(REDIS_CLIENT_INFO_KEY.format(server_id=server_id))
            if not raw:
                return None
            return OAuthClientInformationFull(**json.loads(raw))
    except Exception as exc:
        logger.warning("Could not read stored client_info for %s: %s", server_id, exc)
    return None


def build_oauth_provider(server: MCPServerConfig) -> CompaRAGOAuthProvider:
    """Build an OAuthClientProvider for an OAuth2-authenticated MCP server.

    Token storage: Redis in production, file on disk for local dev. Tokens are
    seeded by ``POST /admin/tool-arena/oauth/seed`` after running
    ``scripts/auth_setup.py`` locally.

    Client_info handling: pre-seeded from env (client_id + secret env var). If
    the secret env var is missing or empty, we keep any previously-stored
    client_info untouched — overwriting it with an empty secret would
    permanently break refresh until the next manual auth_setup run.
    """
    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")

    storage = _get_storage(server.id)

    client_metadata = OAuthClientMetadata(
        redirect_uris=["http://localhost:9876/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        client_name="CompaRAG Tool Arena",
        scope="claudeai openid offline_access",
        token_endpoint_auth_method="client_secret_post",
    )

    if client_secret:
        client_info = OAuthClientInformationFull(
            client_id=auth.client_id,
            client_secret=client_secret,
            redirect_uris=["http://localhost:9876/callback"],
            token_endpoint_auth_method="client_secret_post",
        )
        if isinstance(storage, FileTokenStorage):
            p = storage._dir / "client_info.json"
            p.write_text(client_info.model_dump_json(indent=2))
        elif isinstance(storage, RedisTokenStorage):
            storage._redis.set(
                REDIS_CLIENT_INFO_KEY.format(server_id=server.id),
                client_info.model_dump_json(),
            )
    else:
        # Env var missing/empty — do NOT overwrite stored client_info.
        # If nothing is stored either, the SDK will see no client_info and the
        # call will fail with a clear OAuthTokenError rather than silently
        # using a None-secret provider.
        existing = _read_stored_client_info(storage, server.id)
        if existing is None:
            logger.error(
                "OAuth misconfiguration for %s: env var %s is unset and no "
                "stored client_info exists. Calls will fail until "
                "auth_setup is run or %s is set.",
                server.id,
                auth.client_secret_env,
                auth.client_secret_env,
            )
        else:
            logger.warning(
                "OAuth env var %s is unset for %s; reusing stored client_info.",
                auth.client_secret_env,
                server.id,
            )

    return CompaRAGOAuthProvider(
        token_url=auth.token_url,
        server_id=server.id,
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


def _invalidate_cache(server_id: str) -> None:
    """Drop the cached OAuth provider for one server.

    Called after the admin re-key endpoint writes new tokens so the next call
    to ``get_oauth_provider`` rebuilds with the freshly seeded storage.
    """
    _provider_cache.pop(server_id, None)


async def seed_tokens(
    server: MCPServerConfig,
    refresh_token: str,
    access_token: str | None = None,
    expires_in: int | None = None,
) -> None:
    """Write a freshly-minted refresh_token (+ optional access_token) to storage.

    Used by the admin re-key endpoint. If ``access_token`` is None we write a
    sentinel + 1s expiry so the SDK refreshes on first use.
    """
    storage = _get_storage(server.id)
    token = OAuthToken(
        access_token=access_token or "bootstrap-pending-refresh",
        token_type="Bearer",
        refresh_token=refresh_token,
        expires_in=expires_in if access_token else 1,
    )
    await storage.set_tokens(token)


async def prewarm_oauth_provider(server: MCPServerConfig) -> bool:
    """Open a brief MCP session to trigger OAuth metadata discovery + token refresh.

    The first user request would otherwise pay this cold-start cost (and risk
    exceeding MCP_CALL_TIMEOUT), which is the cause of "first call fails, then
    works" reports. By doing it at app startup, the access_token is already
    fresh in storage and the OAuth metadata is cached on the provider when
    real traffic arrives.

    Failures are logged and swallowed — startup MUST NOT be blocked by a
    misconfigured or unreachable server.
    """
    if not server.auth or server.auth.type != "oauth2":
        return True

    # Local imports to avoid pulling MCP transports at module import time.
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async def _handshake() -> None:
        provider = get_oauth_provider(server)
        async with streamablehttp_client(
            str(server.endpoint),
            headers={},
            auth=provider,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

    try:
        await asyncio.wait_for(_handshake(), timeout=PREWARM_TIMEOUT_SECONDS)
        logger.info("OAuth pre-warm succeeded for %s", server.id)
        return True
    except asyncio.TimeoutError:
        logger.warning(
            "OAuth pre-warm timed out for %s after %ss",
            server.id, PREWARM_TIMEOUT_SECONDS,
        )
        return False
    except Exception as exc:
        logger.warning(
            "OAuth pre-warm failed for %s: %s: %s",
            server.id, type(exc).__name__, exc,
        )
        return False


async def prewarm_all_oauth_providers(servers: list[MCPServerConfig]) -> None:
    """Concurrently pre-warm every OAuth-authenticated server in the list."""
    oauth_servers = [s for s in servers if s.auth and s.auth.type == "oauth2"]
    if not oauth_servers:
        return
    logger.info(
        "Pre-warming OAuth for %d MCP server(s): %s",
        len(oauth_servers),
        [s.id for s in oauth_servers],
    )
    await asyncio.gather(
        *(prewarm_oauth_provider(s) for s in oauth_servers),
        return_exceptions=True,
    )
