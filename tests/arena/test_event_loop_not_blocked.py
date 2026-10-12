"""
A slow model provider must not slow the other requests of the same process.

A comparison is started against the fake provider while cheap requests (sign-in
config, model list) are sent from other threads, and the longest wait of those
is measured. The bound is far above what a cheap request costs and far below
the delays given to the provider, so it only fails when the event loop is held.
"""

import threading
import time

BOUND = 0.4


def warm_up(arena) -> None:
    """One full comparison and the cheap routes first, so that what is measured
    is a process in steady state, not the lazy imports of its first request."""
    delays = (arena.provider.token_delay, arena.provider.first_byte_delay)
    rate_limited = arena.provider.rate_limited_first
    arena.provider.token_delay = arena.provider.first_byte_delay = 0.0
    arena.provider.rate_limited_first = 0
    arena.ask()
    arena.client.get("/api/auth/config")
    arena.client.get("/api/models/")
    arena.provider.token_delay, arena.provider.first_byte_delay = delays
    arena.provider.rate_limited_first = rate_limited
    arena.provider.requests.clear()


def ask_in_background(arena) -> threading.Thread:
    thread = threading.Thread(target=arena.ask, daemon=True)
    thread.start()
    return thread


def slowest_cheap_request_while(
    arena,
    thread: threading.Thread,
    paths: tuple[str, ...] = ("/api/auth/config", "/api/models/"),
) -> float:
    slowest = 0.0
    while thread.is_alive():
        for path in paths:
            started = time.perf_counter()
            assert arena.client.get(path).status_code == 200
            slowest = max(slowest, time.perf_counter() - started)
        time.sleep(0.02)
    return slowest


def test_cheap_requests_stay_fast_while_a_provider_streams_slowly(arena):
    arena.provider.tokens = ["un", " deux", " trois", " quatre", " cinq"]
    arena.provider.token_delay = 0.4
    warm_up(arena)

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND


def test_cheap_requests_stay_fast_while_a_provider_delays_its_first_byte(arena):
    arena.provider.first_byte_delay = 2.0
    warm_up(arena)

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND


def test_cheap_requests_stay_fast_while_a_provider_answers_429_first(arena):
    arena.provider.rate_limited_first = 2
    warm_up(arena)

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND
    assert len(arena.provider.requests) == 4


def test_a_repeated_prompt_is_served_from_the_response_cache(arena, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "CACHE_ENABLED", True)
    monkeypatch.setattr(settings, "CACHE_PROBABILITY", 1.0)

    arena.ask()
    asked = len(arena.provider.requests)
    events = arena.ask()

    assert len(arena.provider.requests) == asked
    assert events[-1] == {"type": "complete"}
