"""
A slow Redis must not hold the event loop while the arena waits on it.

The rate limit check reads four counters. With every Redis command taking a
quarter of a second, the check takes a second, and a heartbeat running next to
it must keep ticking all along.
"""

import asyncio

from backend.arena import session

LATENCY = 0.25


async def longest_gap_while(work) -> float:
    longest = 0.0
    running = True

    async def heartbeat():
        nonlocal longest
        loop = asyncio.get_running_loop()
        last = loop.time()
        while running:
            await asyncio.sleep(0.01)
            now = loop.time()
            longest = max(longest, now - last)
            last = now

    beat = asyncio.create_task(heartbeat())
    try:
        await work
    finally:
        running = False
        await beat
    return longest


def test_the_rate_limit_check_does_not_hold_the_loop_on_a_slow_redis(fake_redis):
    fake_redis.latency = LATENCY

    async def scenario():
        limited = None

        async def check():
            nonlocal limited
            limited = await session.is_ratelimited("session", "1.1.1.1")

        gap = await longest_gap_while(check())
        return limited, gap

    limited, gap = asyncio.run(scenario())

    assert limited is False
    assert gap < LATENCY / 2
    # The four budgets were really read, one command after the other.
    assert len(fake_redis.calls) == 4
