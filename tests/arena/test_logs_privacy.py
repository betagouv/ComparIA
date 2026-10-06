"""
What the logs are allowed to hold.

The JSON logs are kept 12 months and shipped to Loki, and every line of a
request reaches Sentry as a breadcrumb. A prompt, an IP address or an email
address has no business in either. Each test drives the code path that used
to write one and reads what was logged.

Run with pytest, or directly:
    uv run python tests/arena/test_logs_privacy.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402

import backend.arena.session as session  # noqa: E402
import backend.arena.web_search as web_search  # noqa: E402
import backend.auth.email as email  # noqa: E402

PROMPT = "Je m'appelle Camille Martin et j'habite 12 rue des Lilas"
IP = "203.0.113.7"
ADDRESS = "camille@example.org"


class FakeRedis:
    def __init__(self, fail=False):
        self.fail = fail
        self.store = {}

    def _check(self):
        if self.fail:
            raise ConnectionError("redis is down")

    def get(self, key):
        self._check()
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self._check()
        self.store[key] = value

    def incr(self, key):
        self._check()

    def expire(self, key, ttl):
        self._check()


class Captured(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


@pytest.fixture
def logged():
    """Every line the 'languia' logger writes during the test."""
    handler = Captured()
    logger = logging.getLogger("languia")
    level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler.lines
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)


def test_the_web_search_cache_logs_no_prompt(logged):
    redis = FakeRedis()
    with (
        patch.object(web_search.settings, "CACHE_ENABLED", True),
        patch.object(web_search, "get_redis_client", lambda: redis),
    ):
        web_search.store_cached_search_results(PROMPT, [])
        redis.store = {
            key: '[{"name": "n", "url": "u", "content": "c"}]' for key in redis.store
        }
        assert web_search.get_cached_web_search(PROMPT)

    assert any("Stored web search cache" in line for line in logged)
    assert any("Web search cache hit" in line for line in logged)
    assert not any("Camille" in line for line in logged)


def test_a_redis_failure_logs_no_ip(logged):
    redis = FakeRedis(fail=True)
    with patch.object(session, "get_redis_client", lambda: redis):
        session.increment_blocked_prompts(IP)
        assert session.is_block_cooldown(IP) is False

    assert len(logged) == 2
    assert all("redis is down" in line for line in logged)
    assert not any(IP in line for line in logged)


@pytest.mark.parametrize(
    "send",
    [
        lambda: email.send_login_code(ADDRESS, "123456"),
        lambda: email.send_invite_link(ADDRESS, "https://host/invite/token"),
    ],
)
def test_without_smtp_no_address_is_logged(logged, send):
    with (
        patch.object(email.settings, "SMTP_HOST", None),
        patch.object(email.settings, "LANGUIA_DEBUG", False),
    ):
        asyncio.run(send())

    assert any("SMTP is not configured" in line for line in logged)
    assert not any(ADDRESS in line for line in logged)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
