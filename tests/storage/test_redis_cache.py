"""
The cache shared across instances through Redis (no real Redis).

Each `@redis_cache` function keeps its result in process memory under a key
kept in Redis: changing the key from anywhere makes every instance recompute.
Two decorated functions with the same Redis key stand for two instances.
"""

import asyncio
import time

from utils.storage.redis import invalidate_cache, redis_cache

KEY = "test:cache-key"


def counted():
    """A decorated function and the list of the calls it really ran."""
    calls: list[int] = []

    @redis_cache(KEY)
    async def load() -> int:
        calls.append(1)
        return len(calls)

    return load, calls


def test_a_result_is_computed_once_until_invalidated(fake_redis):
    async def scenario():
        load, calls = counted()
        assert await load() == 1
        assert await load() == 1
        await invalidate_cache(KEY)
        assert await load() == 2
        assert len(calls) == 2

    asyncio.run(scenario())


def test_invalidating_on_one_instance_refreshes_the_others(fake_redis):
    async def scenario():
        first, first_calls = counted()
        second, second_calls = counted()
        await first()
        await second()
        assert (len(first_calls), len(second_calls)) == (1, 1)

        await invalidate_cache(KEY)

        await first()
        await second()
        assert (len(first_calls), len(second_calls)) == (2, 2)

    asyncio.run(scenario())


def test_nothing_is_cached_and_nothing_crashes_when_redis_is_down(fake_redis):
    fake_redis.failure = ConnectionError("redis is down")

    async def scenario():
        load, calls = counted()
        assert await load() == 1
        assert await load() == 2
        await invalidate_cache(KEY)  # does not raise either
        assert len(calls) == 2

    asyncio.run(scenario())


def test_a_slow_redis_does_not_delay_a_request_that_does_not_need_it(fake_redis):
    fake_redis.latency = 0.3

    async def scenario():
        # Requests served without Redis, as often as the loop lets them.
        gaps: list[float] = []

        async def unrelated_requests():
            last = time.monotonic()
            while True:
                await asyncio.sleep(0.01)
                now = time.monotonic()
                gaps.append(now - last)
                last = now

        ticker = asyncio.create_task(unrelated_requests())
        load, _ = counted()
        await load()  # waits on Redis for a good part of a second
        ticker.cancel()
        return max(gaps)

    assert asyncio.run(scenario()) < 0.15
