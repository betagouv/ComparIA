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


def ask_in_background(arena) -> threading.Thread:
    thread = threading.Thread(target=arena.ask, daemon=True)
    thread.start()
    return thread


def slowest_cheap_request_while(arena, thread: threading.Thread) -> float:
    slowest = 0.0
    while thread.is_alive():
        for path in ("/api/auth/config", "/api/models/"):
            started = time.perf_counter()
            assert arena.client.get(path).status_code == 200
            slowest = max(slowest, time.perf_counter() - started)
        time.sleep(0.02)
    return slowest


def test_cheap_requests_stay_fast_while_a_provider_streams_slowly(arena):
    arena.provider.tokens = ["un", " deux", " trois", " quatre", " cinq"]
    arena.provider.token_delay = 0.4
    arena.client.get("/api/auth/config")
    arena.client.get("/api/models/")

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND


def test_cheap_requests_stay_fast_while_a_provider_delays_its_first_byte(arena):
    arena.provider.first_byte_delay = 2.0
    arena.client.get("/api/auth/config")
    arena.client.get("/api/models/")

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND


def test_cheap_requests_stay_fast_while_a_provider_answers_429_first(arena):
    arena.provider.rate_limited_first = 2
    arena.client.get("/api/auth/config")
    arena.client.get("/api/models/")

    slowest = slowest_cheap_request_while(arena, ask_in_background(arena))

    assert slowest < BOUND
    assert len(arena.provider.requests) == 4
