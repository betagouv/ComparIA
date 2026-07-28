"""
Unit tests for the email-login rate limits (no network, no real Redis, no DB).

Covers the 600-kids-behind-one-IP property (per-email request cap is isolated
per email, never shared across a NAT) and the verify brute-force limiter.

Run with pytest, or directly:
    uv run python tests/arena/test_auth_ratelimit.py
"""

import contextlib
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import utils.database.models  # noqa: F401 needed before importing backend.auth.router

import backend.auth.router as auth_router
from backend.config import settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from utils.storage.redis import REDIS_AUTH_EMAIL_REQ, REDIS_AUTH_VERIFY_FAIL


class FakeRedis:
    """Minimal string-counter stub matching decode_responses=True behaviour."""

    def __init__(self):
        self.store: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        pass

    def get(self, key):
        v = self.store.get(key)
        return None if v is None else str(v)

    def delete(self, key):
        self.store.pop(key, None)


async def _fake_request_login_code(email):
    return "123456"


async def _fake_send_login_code(email, code):
    pass


async def _fake_get_app_settings():
    return SimpleNamespace(auth_domain_allowlist=None)


@contextlib.contextmanager
def fake_router(verify_login_code=None):
    fake = FakeRedis()

    orig = {
        "get_redis_client": auth_router.get_redis_client,
        "verify_altcha_token": auth_router.verify_altcha_token,
        "request_login_code": auth_router.request_login_code,
        "send_login_code": auth_router.send_login_code,
        "verify_login_code": auth_router.verify_login_code,
        "get_app_settings": auth_router.get_app_settings,
    }
    auth_router.get_redis_client = lambda: fake
    auth_router.verify_altcha_token = lambda payload: (True, None)
    auth_router.request_login_code = _fake_request_login_code
    auth_router.send_login_code = _fake_send_login_code
    auth_router.get_app_settings = _fake_get_app_settings
    if verify_login_code is not None:
        auth_router.verify_login_code = verify_login_code
    try:
        app = FastAPI()
        app.include_router(auth_router.router)
        yield TestClient(app), fake
    finally:
        for name, func in orig.items():
            setattr(auth_router, name, func)


def test_per_email_request_cap_is_isolated_per_email():
    with fake_router() as (client, _fake):
        limit = settings.AUTH_EMAIL_REQUEST_PER_EMAIL_PER_HOUR
        for _ in range(limit):
            r = client.post(
                "/auth/email/request",
                json={"email": "student1@school.fr", "altcha_payload": "x"},
            )
            assert r.status_code == 204

        r = client.post(
            "/auth/email/request",
            json={"email": "student1@school.fr", "altcha_payload": "x"},
        )
        assert r.status_code == 429

        # Same IP, different student: independent bucket, must not be blocked.
        r = client.post(
            "/auth/email/request",
            json={"email": "student2@school.fr", "altcha_payload": "x"},
        )
        assert r.status_code == 204


def test_per_ip_request_cap_uses_configured_ceiling():
    with fake_router() as (client, fake):
        ip_limit = settings.AUTH_EMAIL_REQUEST_PER_IP_PER_HOUR
        email_limit = settings.AUTH_EMAIL_REQUEST_PER_EMAIL_PER_HOUR
        assert ip_limit > email_limit, "IP ceiling must stay looser than the email cap"

        key = REDIS_AUTH_EMAIL_REQ.format(ip="testclient")
        fake.store[key] = ip_limit  # fast-forward to the edge without ip_limit requests

        r = client.post(
            "/auth/email/request",
            json={"email": "student3@school.fr", "altcha_payload": "x"},
        )
        assert r.status_code == 429


def test_verify_fail_counter_trips_at_max_attempts():
    async def always_wrong(**kwargs):
        return None

    with fake_router(verify_login_code=always_wrong) as (client, _fake):
        max_attempts = settings.AUTH_VERIFY_MAX_ATTEMPTS
        for _ in range(max_attempts):
            r = client.post(
                "/auth/email/verify",
                json={"email": "student1@school.fr", "code": "000000"},
            )
            assert r.status_code == 400

        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
        )
        assert r.status_code == 429


def test_verify_fail_counter_is_isolated_per_email():
    async def always_wrong(**kwargs):
        return None

    with fake_router(verify_login_code=always_wrong) as (client, _fake):
        max_attempts = settings.AUTH_VERIFY_MAX_ATTEMPTS
        for _ in range(max_attempts):
            r = client.post(
                "/auth/email/verify",
                json={"email": "student1@school.fr", "code": "000000"},
            )
            assert r.status_code == 400

        # Same IP, different student: independent bucket, must not be blocked.
        r = client.post(
            "/auth/email/verify",
            json={"email": "student2@school.fr", "code": "000000"},
        )
        assert r.status_code == 400


def test_successful_verify_clears_fail_counter():
    calls = {"n": 0}

    async def wrong_then_right(**kwargs):
        calls["n"] += 1
        return None if calls["n"] == 1 else "sometoken"

    with fake_router(verify_login_code=wrong_then_right) as (client, fake):
        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
        )
        assert r.status_code == 400

        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "111111"},
        )
        assert r.status_code == 200
        assert "auth_session" in r.cookies

        key = REDIS_AUTH_VERIFY_FAIL.format(
            ip="testclient", email=auth_router._hash("student1@school.fr")
        )
        assert key not in fake.store


def test_new_code_request_resets_verify_counter():
    async def always_wrong(**kwargs):
        return None

    with fake_router(verify_login_code=always_wrong) as (client, _fake):
        for _ in range(settings.AUTH_VERIFY_MAX_ATTEMPTS):
            client.post(
                "/auth/email/verify",
                json={"email": "student1@school.fr", "code": "000000"},
            )
        # Locked out.
        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
        )
        assert r.status_code == 429

        # Requesting a fresh code clears the counter; verify is attemptable again.
        r = client.post(
            "/auth/email/request",
            json={"email": "student1@school.fr", "altcha_payload": "x"},
        )
        assert r.status_code == 204

        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
        )
        assert r.status_code == 400


def test_verify_lockout_is_scoped_per_ip():
    async def always_wrong(**kwargs):
        return None

    with fake_router(verify_login_code=always_wrong) as (client, _fake):
        # An attacker who knows a victim's email burns all attempts from its IP.
        for _ in range(settings.AUTH_VERIFY_MAX_ATTEMPTS):
            client.post(
                "/auth/email/verify",
                json={"email": "victim@school.fr", "code": "000000"},
            )
        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
        )
        assert r.status_code == 429  # attacker's own IP is locked

        # The victim, from another IP, is not locked out (no cross-IP DoS).
        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
            headers={"x-forwarded-for": "203.0.113.7"},
        )
        assert r.status_code == 400


def run():
    test_per_email_request_cap_is_isolated_per_email()
    test_per_ip_request_cap_uses_configured_ceiling()
    test_verify_fail_counter_trips_at_max_attempts()
    test_verify_fail_counter_is_isolated_per_email()
    test_successful_verify_clears_fail_counter()
    test_new_code_request_resets_verify_counter()
    test_verify_lockout_is_scoped_per_ip()
    print("All auth rate limit cases passed.")


if __name__ == "__main__":
    run()
