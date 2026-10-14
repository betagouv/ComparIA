"""
A Redis stand-in for the arena tests, with expiry on a clock the test moves.

It answers like `redis.Redis(decode_responses=True)`: strings from GET, ints
from INCRBY, and -2 / -1 from TTL for a missing key and a key with no expiry.
Kept by hand rather than taken from `fakeredis`: tests need to move time
forward to watch a window close, and to make Redis fail between two calls.
"""

import contextlib
from datetime import datetime

from redis.exceptions import ConnectionError as RedisConnectionError


class FakeRedis:
    """`pipelines_that_work` makes every pipeline after that many fail, as when
    Redis drops between two calls."""

    def __init__(self, pipelines_that_work=None, now=1_800_000_000.0):
        self.store: dict[str, object] = {}
        self.expires_at: dict[str, float] = {}
        self.now = now
        self.pipelines_left = pipelines_that_work

    def advance(self, seconds):
        self.now += seconds

    def _live(self, key):
        if key in self.expires_at and self.expires_at[key] <= self.now:
            del self.store[key]
            del self.expires_at[key]
        return key in self.store

    def get(self, key):
        return str(self.store[key]) if self._live(key) else None

    def mget(self, *keys):
        if len(keys) == 1 and isinstance(keys[0], (list, tuple)):
            keys = keys[0]
        return [self.get(key) for key in keys]

    def set(self, key, value, ex=None, nx=False):
        if nx and self._live(key):
            return None
        self.store[key] = value
        self.expires_at.pop(key, None)
        if ex is not None:
            self.expires_at[key] = self.now + ex
        return True

    def setex(self, key, seconds, value):
        return self.set(key, value, ex=seconds)

    def incrby(self, key, amount):
        value = int(self.store[key]) + amount if self._live(key) else amount
        self.store[key] = value
        return value

    def incr(self, key):
        return self.incrby(key, 1)

    def decrby(self, key, amount):
        return self.incrby(key, -amount)

    def expire(self, key, seconds, nx=False):
        if not self._live(key) or (nx and key in self.expires_at):
            return False
        self.expires_at[key] = self.now + seconds
        return True

    def expireat(self, key, when):
        if isinstance(when, datetime):
            when = when.timestamp()
        if not self._live(key):
            return False
        self.expires_at[key] = float(when)
        return True

    def ttl(self, key):
        if not self._live(key):
            return -2
        if key not in self.expires_at:
            return -1
        return int(self.expires_at[key] - self.now)

    def delete(self, *keys):
        deleted = [key for key in keys if self._live(key)]
        for key in deleted:
            del self.store[key]
            self.expires_at.pop(key, None)
        return len(deleted)

    def hincrby(self, key, field, amount=1):
        fields = self.store[key] if self._live(key) else {}
        assert isinstance(fields, dict), f"{key} is not a hash"
        fields[field] = int(fields.get(field, 0)) + amount
        self.store[key] = fields
        return fields[field]

    def hgetall(self, key):
        if not self._live(key):
            return {}
        fields = self.store[key]
        assert isinstance(fields, dict), f"{key} is not a hash"
        return {name: str(value) for name, value in fields.items()}

    def pipeline(self, transaction=True):
        return FakePipeline(self)


class FakePipeline:
    """Queues calls and runs them in order on `execute`, as MULTI/EXEC does."""

    def __init__(self, redis):
        self.redis = redis
        self.calls = []

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return queue

    def execute(self):
        if self.redis.pipelines_left is not None:
            if self.redis.pipelines_left == 0:
                raise RedisConnectionError("Redis went away")
            self.redis.pipelines_left -= 1
        results = [
            getattr(self.redis, name)(*args, **kwargs)
            for name, args, kwargs in self.calls
        ]
        self.calls = []
        return results


@contextlib.contextmanager
def fake_redis(*modules, fake=None):
    """Point `get_redis_client` of each module at one fake."""
    fake = fake or FakeRedis()
    originals = [module.get_redis_client for module in modules]
    for module in modules:
        module.get_redis_client = lambda: fake
    try:
        yield fake
    finally:
        for module, original in zip(modules, originals):
            module.get_redis_client = original
