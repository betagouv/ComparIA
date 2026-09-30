"""
An in-memory Redis for the tests, for the synchronous and the asynchronous
client alike.

Both facades share one store, so a test can write through one client and read
through the other. `install` replaces the client classes themselves, which is
the lowest place to cut: whichever module builds a client, and whichever of the
two it builds, gets this one.
"""

import time
from typing import Any

import redis
import redis.asyncio


class FakeStore:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.expires: dict[str, float] = {}
        # Set to an exception to make every command fail, like a Redis outage.
        self.failure: Exception | None = None
        # Seconds every command takes, to simulate a slow Redis.
        self.latency = 0.0
        self.calls: list[tuple] = []

    def _alive(self, key: str) -> bool:
        deadline = self.expires.get(key)
        if deadline is not None and deadline <= time.monotonic():
            self.data.pop(key, None)
            self.expires.pop(key, None)
        return key in self.data

    def run(self, command: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((command, *args))
        if self.failure:
            raise self.failure
        return getattr(self, f"_{command}")(*args, **kwargs)

    def _ping(self) -> bool:
        return True

    def _get(self, key: str) -> Any:
        return self.data[key] if self._alive(key) else None

    def _getdel(self, key: str) -> Any:
        value = self._get(key)
        self.data.pop(key, None)
        return value

    def _set(self, key: str, value: Any, ex=None, nx=False, **_: Any) -> Any:
        if nx and self._alive(key):
            return None
        self.data[key] = str(value)
        if ex is not None:
            self.expires[key] = time.monotonic() + ex
        else:
            self.expires.pop(key, None)
        return True

    def _setex(self, key: str, ttl: int, value: Any) -> bool:
        return self._set(key, value, ex=ttl)

    def _incrby(self, key: str, amount: int = 1) -> int:
        value = int(self._get(key) or 0) + amount
        self.data[key] = str(value)
        return value

    def _incr(self, key: str) -> int:
        return self._incrby(key, 1)

    def _expire(self, key: str, ttl: int) -> bool:
        if not self._alive(key):
            return False
        self.expires[key] = time.monotonic() + ttl
        return True

    def _delete(self, *keys: str) -> int:
        removed = sum(1 for key in keys if self._alive(key))
        for key in keys:
            self.data.pop(key, None)
            self.expires.pop(key, None)
        return removed


COMMANDS = (
    "ping",
    "get",
    "getdel",
    "set",
    "setex",
    "incr",
    "incrby",
    "expire",
    "delete",
)


def _sync_client(store: FakeStore):
    class SyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    for command in COMMANDS:

        def method(self, *args: Any, _command=command, **kwargs: Any) -> Any:
            time.sleep(store.latency)
            return store.run(_command, *args, **kwargs)

        setattr(SyncClient, command, method)
    return SyncClient


def _async_client(store: FakeStore):
    import asyncio

    class AsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    for command in COMMANDS:

        async def method(self, *args: Any, _command=command, **kwargs: Any) -> Any:
            await asyncio.sleep(store.latency)
            return store.run(_command, *args, **kwargs)

        setattr(AsyncClient, command, method)
    return AsyncClient


def _drop_built_clients() -> None:
    """The clients are built once and kept: forget the ones already built."""
    from utils.storage import redis as storage

    for name in ("get_redis_client", "get_async_redis_client"):
        if hasattr(storage, name):
            getattr(storage, name).cache_clear()


def install(monkeypatch) -> FakeStore:
    """Replace the Redis clients with fakes sharing one store.

    Call `uninstall` when done: the fake clients would otherwise stay cached.
    """
    store = FakeStore()
    monkeypatch.setattr(redis, "Redis", _sync_client(store))
    monkeypatch.setattr(redis.asyncio, "Redis", _async_client(store))
    _drop_built_clients()
    return store


def uninstall() -> None:
    _drop_built_clients()
