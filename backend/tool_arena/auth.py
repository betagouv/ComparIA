"""OAuth2 client_credentials token cache for MCP server authentication.

Provides get_token() which fetches an OAuth2 token via client_credentials grant
and caches it with a TTL buffer of 30 seconds before expiry.
"""

import asyncio
import logging
import os
import time

import httpx

from backend.tool_arena.config import OAuth2Auth

logger = logging.getLogger("tool_arena.auth")

# Module-level token cache: server_id -> (access_token, expiry_monotonic)
_token_cache: dict[str, tuple[str, float]] = {}

# Lazy-initialized lock (avoids "no running event loop" at import time)
_refresh_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    """Return the module-level async lock, creating it if needed."""
    global _refresh_lock
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    return _refresh_lock


async def get_token(server_id: str, auth: OAuth2Auth) -> str:
    """Fetch or return a cached OAuth2 token for the given server.

    Uses client_credentials grant. Caches token with a 30-second early-expiry
    buffer to avoid using tokens that expire mid-request.

    Args:
        server_id: Unique identifier for the MCP server (used as cache key).
        auth: OAuth2Auth config with client_id, client_secret_env, token_url.

    Returns:
        A valid access token string.

    Raises:
        KeyError: If the env var specified by auth.client_secret_env is not set.
        httpx.HTTPStatusError: If the token endpoint returns a non-2xx response.
    """
    now = time.monotonic()

    # Fast path: valid cached token
    if server_id in _token_cache:
        cached_token, expiry = _token_cache[server_id]
        if now < expiry - 30:
            return cached_token

    # Slow path: acquire lock and refresh
    async with _get_lock():
        # Double-check after acquiring lock (another coroutine may have refreshed)
        now = time.monotonic()
        if server_id in _token_cache:
            cached_token, expiry = _token_cache[server_id]
            if now < expiry - 30:
                return cached_token

        client_secret = os.environ[auth.client_secret_env]  # KeyError if missing

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                auth.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": auth.client_id,
                    "client_secret": client_secret,
                },
            )
            resp.raise_for_status()

        payload = resp.json()
        access_token: str = payload["access_token"]
        expires_in: int = payload.get("expires_in", 3600)

        _token_cache[server_id] = (access_token, time.monotonic() + expires_in)
        logger.debug("Fetched new token for server '%s' (expires_in=%s)", server_id, expires_in)
        return access_token


def _clear_token_cache() -> None:
    """Clear the in-memory token cache. Used for test isolation."""
    _token_cache.clear()
