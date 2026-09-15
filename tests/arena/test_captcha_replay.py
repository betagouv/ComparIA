"""
Replay prevention for the proof-of-work captcha.

Redis is the only thing between one solved challenge and unlimited replays of
it, so a Redis outage has to close the door, not open it.

Run with pytest, or directly:
    uv run python tests/arena/test_captcha_replay.py
"""

import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.arena.captcha as captcha  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True


class BrokenRedis:
    def set(self, *_args, **_kwargs):
        raise ConnectionError("Redis is down")


@contextlib.contextmanager
def redis_and_solver(client, solved=True):
    originals = (captcha.get_redis_client, captcha.verify_solution)
    captcha.get_redis_client = lambda: client
    captcha.verify_solution = lambda **_kwargs: (solved, None)
    try:
        yield
    finally:
        captcha.get_redis_client, captcha.verify_solution = originals


def test_a_fresh_solution_is_accepted():
    with redis_and_solver(FakeRedis()):
        assert captcha.verify_altcha_token("payload") == (True, None)


def test_the_same_solution_twice_is_refused():
    with redis_and_solver(FakeRedis()):
        captcha.verify_altcha_token("payload")
        ok, _error = captcha.verify_altcha_token("payload")

    assert ok is False


def test_a_redis_outage_refuses_rather_than_waves_through():
    with redis_and_solver(BrokenRedis()):
        ok, _error = captcha.verify_altcha_token("payload")

    assert ok is False


def run():
    test_a_fresh_solution_is_accepted()
    test_the_same_solution_twice_is_refused()
    test_a_redis_outage_refuses_rather_than_waves_through()
    print("Captcha replay cases passed.")


if __name__ == "__main__":
    run()
