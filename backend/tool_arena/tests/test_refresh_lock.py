"""Tests for the Redis distributed refresh lock (Phase 3, ``_with_refresh_lock``)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from mcp.shared.auth import OAuthToken

import backend.tool_arena.auth as auth_module

pytestmark = pytest.mark.anyio


class _FakeRedis:
    """Minimal in-memory Redis stand-in supporting SET NX PX, GET, DELETE."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key, value, nx=False, px=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)
        return 1

    def ping(self):
        return True


def _redis_storage(server_id: str = "srv") -> auth_module.RedisTokenStorage:
    return auth_module.RedisTokenStorage(server_id, _FakeRedis())


async def test_lock_acquired_runs_refresh(tmp_path):
    storage = _redis_storage("srv1")
    called = {"n": 0}

    async def _do_refresh():
        called["n"] += 1
        return "OK"

    result = await auth_module._with_refresh_lock("srv1", storage, _do_refresh)
    assert result == "OK"
    assert called["n"] == 1
    # Lock released
    assert storage._redis.get("oauth_refresh_lock:srv1") is None


async def test_lock_held_waiter_returns_none_when_fresh_token_appears(tmp_path):
    storage = _redis_storage("srv2")
    # Pre-acquire the lock as if another replica holds it.
    storage._redis.set("oauth_refresh_lock:srv2", "other-holder", nx=True, px=30000)

    # Simulate the peer writing a fresh token before our first backoff wakes.
    fresh = OAuthToken(
        access_token="brand-new", token_type="Bearer", refresh_token="rt2"
    )
    await storage.set_tokens(fresh)

    async def _do_refresh():
        raise AssertionError("should not run when peer already refreshed")

    result = await auth_module._with_refresh_lock("srv2", storage, _do_refresh)
    assert result is None


async def test_file_storage_skips_lock(tmp_path):
    with patch.object(auth_module, "TOKENS_DIR", tmp_path):
        storage = auth_module.FileTokenStorage("srv3")

    called = {"n": 0}

    async def _do_refresh():
        called["n"] += 1
        return "ran"

    result = await auth_module._with_refresh_lock("srv3", storage, _do_refresh)
    assert result == "ran"
    assert called["n"] == 1
