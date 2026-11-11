"""
Unit tests for the email-login rate limits (no network, no real Redis, no DB).

Covers the 600-kids-behind-one-IP property (per-email request cap is isolated
per email, never shared across a NAT), the verify brute-force limiter, the fact
that the throttle answers before the consent gate, and that a client cannot pick
the IP it is counted under.

Run with pytest, or directly:
    uv run python tests/arena/test_auth_ratelimit.py
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.auth.router as auth_router
import utils.database.models  # noqa: F401 needed before importing backend.auth.router
from backend.auth.services import LoginResult
from backend.config import ANONYMOUS_SESSION_COOKIE, settings
from utils.storage.redis import REDIS_AUTH_EMAIL_REQ, REDIS_AUTH_VERIFY_FAIL


class FakePipeline:
    """Queues commands and runs them in one go, as MULTI/EXEC would."""

    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self.commands.append((name, args, kwargs))

        return queue

    def execute(self):
        return [getattr(self.redis, n)(*a, **k) for n, a, k in self.commands]


class FakeRedis:
    """Minimal string-counter stub matching decode_responses=True behaviour."""

    def __init__(self):
        self.store: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        pass

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = int(value)
        return True

    def pipeline(self, transaction=True):
        return FakePipeline(self)

    def get(self, key):
        v = self.store.get(key)
        return None if v is None else str(v)

    def delete(self, key):
        self.store.pop(key, None)


async def _fake_request_login_code(email):
    return "123456"


async def _fake_send_login_code(email, code, **_colors):
    pass


async def _fake_get_app_settings():
    return SimpleNamespace(
        auth_methods=["email_code"],
        auth_domain_allowlist=None,
        platform_name="Compar:IA",
        primary_color_light="#6464F3",
        secondary_color_light="#FF9575",
        default_locale="fr",
    )


async def _fake_current_acceptance(**kwargs):
    return True


async def _fake_missing_acceptance(**kwargs):
    return False


@contextlib.contextmanager
def trusted_proxies(count):
    """Run the block as if the app sat behind `count` reverse proxies."""
    original = settings.COMPARIA_TRUSTED_PROXY_COUNT
    settings.COMPARIA_TRUSTED_PROXY_COUNT = count
    try:
        yield
    finally:
        settings.COMPARIA_TRUSTED_PROXY_COUNT = original


@contextlib.contextmanager
def fake_router(verify_login_code=None, has_current_terms_acceptance=None):
    fake = FakeRedis()

    orig = {
        "get_redis_client": auth_router.get_redis_client,
        "verify_altcha_token": auth_router.verify_altcha_token,
        "request_login_code": auth_router.request_login_code,
        "send_login_code": auth_router.send_login_code,
        "verify_login_code": auth_router.verify_login_code,
        "get_app_settings": auth_router.get_app_settings,
        "has_current_terms_acceptance": auth_router.has_current_terms_acceptance,
    }
    auth_router.get_redis_client = lambda: fake
    auth_router.verify_altcha_token = lambda payload: (True, None)
    auth_router.request_login_code = _fake_request_login_code
    auth_router.send_login_code = _fake_send_login_code
    auth_router.get_app_settings = _fake_get_app_settings
    auth_router.has_current_terms_acceptance = (
        has_current_terms_acceptance or _fake_current_acceptance
    )
    if verify_login_code is not None:
        auth_router.verify_login_code = verify_login_code
    try:
        app = FastAPI()
        app.include_router(auth_router.router)
        client = TestClient(app)
        # The consent gate reads the anonymous session, and the middleware that
        # mints it is not mounted here. These tests are about the throttle.
        client.cookies.set(ANONYMOUS_SESSION_COOKIE, "anonymous-test-token")
        yield client, fake
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


def test_request_cap_answers_before_the_consent_gate():
    """The gate sits after the throttle on purpose. If it moved ahead of it, a
    visitor who never accepted could hammer the endpoint uncapped."""
    with fake_router(has_current_terms_acceptance=_fake_missing_acceptance) as (
        client,
        fake,
    ):
        key = REDIS_AUTH_EMAIL_REQ.format(ip="testclient")
        fake.store[key] = settings.AUTH_EMAIL_REQUEST_PER_IP_PER_HOUR

        r = client.post(
            "/auth/email/request",
            json={"email": "student4@school.fr", "altcha_payload": "x"},
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
        return (
            None
            if calls["n"] == 1
            else LoginResult(kind="session", token="sometoken", first=False)
        )

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

    with (
        fake_router(verify_login_code=always_wrong) as (client, _fake),
        trusted_proxies(1),
    ):
        # An attacker who knows a victim's email burns all attempts from its IP.
        for _ in range(settings.AUTH_VERIFY_MAX_ATTEMPTS):
            client.post(
                "/auth/email/verify",
                json={"email": "victim@school.fr", "code": "000000"},
                headers={"x-forwarded-for": "198.51.100.4"},
            )
        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
            headers={"x-forwarded-for": "198.51.100.4"},
        )
        assert r.status_code == 429  # attacker's own IP is locked

        # The victim, from another IP, is not locked out (no cross-IP DoS).
        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
            headers={"x-forwarded-for": "203.0.113.7"},
        )
        assert r.status_code == 400


def test_forwarded_for_is_ignored_without_trusted_proxies():
    """Untrusted, the header is a free choice of rate limit bucket, which is the
    same as no rate limit at all."""

    async def always_wrong(**kwargs):
        return None

    with (
        fake_router(verify_login_code=always_wrong) as (client, fake),
        trusted_proxies(0),
    ):
        for _ in range(settings.AUTH_VERIFY_MAX_ATTEMPTS):
            client.post(
                "/auth/email/verify",
                json={"email": "victim@school.fr", "code": "000000"},
            )

        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
            headers={"x-forwarded-for": "203.0.113.7"},
        )
        assert r.status_code == 429

        spoofed = REDIS_AUTH_VERIFY_FAIL.format(
            ip="203.0.113.7", email=auth_router._hash("victim@school.fr")
        )
        assert spoofed not in fake.store


def test_per_email_verify_cap_trips_whatever_the_ip():
    """Each IP gets its own bucket, so an attacker with a pool of addresses only
    meets the per-email ceiling."""

    async def always_wrong(**kwargs):
        return None

    with (
        fake_router(verify_login_code=always_wrong) as (client, _fake),
        trusted_proxies(1),
    ):
        for n in range(settings.AUTH_VERIFY_MAX_ATTEMPTS_PER_EMAIL):
            r = client.post(
                "/auth/email/verify",
                json={"email": "victim@school.fr", "code": "000000"},
                headers={"x-forwarded-for": f"203.0.113.{n + 1}"},
            )
            assert r.status_code == 400

        r = client.post(
            "/auth/email/verify",
            json={"email": "victim@school.fr", "code": "000000"},
            headers={"x-forwarded-for": "198.51.100.9"},
        )
        assert r.status_code == 429


def test_verify_refuses_a_cross_site_origin():
    """Login CSRF: a third-party page must not be able to drop its own session
    cookie in a visitor's browser."""

    async def always_right(**kwargs):
        return LoginResult(kind="session", token="sometoken", first=False)

    with fake_router(verify_login_code=always_right) as (client, _fake):
        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
            headers={"origin": "https://attacker.example"},
        )
        assert r.status_code == 403
        assert "auth_session" not in r.cookies

        r = client.post(
            "/auth/email/verify",
            json={"email": "student1@school.fr", "code": "000000"},
            headers={"origin": "http://testserver"},
        )
        assert r.status_code == 200


def _verify_burst(app, codes, forwarded_for=None):
    """Send every guess at once, the way a script would, and wait for all."""

    async def burst():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies={ANONYMOUS_SESSION_COOKIE: "anonymous-test-token"},
        ) as client:
            return await asyncio.gather(
                *(
                    client.post(
                        "/auth/email/verify",
                        json={"email": "victim@school.fr", "code": code},
                        headers=(
                            {"x-forwarded-for": forwarded_for(n)}
                            if forwarded_for
                            else {}
                        ),
                    )
                    for n, code in enumerate(codes)
                )
            )

    return asyncio.run(burst())


def _slow_checker(evaluated, right_code=None):
    async def verify(**kwargs):
        evaluated.append(kwargs["code"])
        # The database round trip, where the other requests get their turn.
        await asyncio.sleep(0.01)
        if kwargs["code"] == right_code:
            return LoginResult("session", "sometoken")
        return None

    return verify


def test_parallel_wrong_codes_from_one_ip_stop_at_the_cap():
    """Guesses sent all at once must meet the same cap as guesses sent one by
    one: a burst cannot slip in between the check and the count."""
    evaluated = []
    with fake_router(verify_login_code=_slow_checker(evaluated)) as (client, _fake):
        codes = [f"{n:06d}" for n in range(60)]
        responses = _verify_burst(client.app, codes)

    cap = settings.AUTH_VERIFY_MAX_ATTEMPTS
    assert len(evaluated) == cap
    statuses = sorted(r.status_code for r in responses)
    assert statuses.count(400) == len(evaluated)
    assert statuses.count(429) == len(codes) - len(evaluated)


def test_parallel_wrong_codes_from_many_ips_stop_at_the_email_cap():
    evaluated = []
    with (
        fake_router(verify_login_code=_slow_checker(evaluated, "123456")) as (
            client,
            _fake,
        ),
        trusted_proxies(1),
    ):
        codes = [f"{n:06d}" for n in range(60)]
        _verify_burst(client.app, codes, forwarded_for=lambda n: f"203.0.113.{n + 1}")
        assert len(evaluated) == settings.AUTH_VERIFY_MAX_ATTEMPTS_PER_EMAIL

        # The right code, once the cap is spent, is refused without a look.
        seen = len(evaluated)
        (r,) = _verify_burst(client.app, ["123456"], lambda _n: "198.51.100.9")
        assert r.status_code == 429
        assert len(evaluated) == seen
        assert "auth_session" not in r.cookies


def test_verify_says_whether_this_is_the_first_sign_in():
    """The sign-in form asks its optional questions of a new account only once:
    the answer comes from the verify call, not from how recent the account is."""

    for first in (True, False):

        async def login_result(first=first, **kwargs):
            return LoginResult(kind="session", token="sometoken", first=first)

        with fake_router(verify_login_code=login_result) as (client, _fake):
            r = client.post(
                "/auth/email/verify",
                json={"email": "student1@school.fr", "code": "000000"},
                headers={"origin": "http://testserver"},
            )
            assert r.status_code == 200
            assert r.json()["first_sign_in"] is first


def run():
    test_per_email_request_cap_is_isolated_per_email()
    test_per_ip_request_cap_uses_configured_ceiling()
    test_request_cap_answers_before_the_consent_gate()
    test_verify_fail_counter_trips_at_max_attempts()
    test_verify_fail_counter_is_isolated_per_email()
    test_successful_verify_clears_fail_counter()
    test_new_code_request_resets_verify_counter()
    test_verify_lockout_is_scoped_per_ip()
    test_forwarded_for_is_ignored_without_trusted_proxies()
    test_per_email_verify_cap_trips_whatever_the_ip()
    test_verify_refuses_a_cross_site_origin()
    test_parallel_wrong_codes_from_one_ip_stop_at_the_cap()
    test_parallel_wrong_codes_from_many_ips_stop_at_the_email_cap()
    test_verify_says_whether_this_is_the_first_sign_in()
    print("All auth rate limit cases passed.")


if __name__ == "__main__":
    run()
