"""
Backend behaviour when the public URL of the Instance has a path.

Every cookie the backend sets or deletes carries the path of the public URL,
the origin check and CORS compare against its origin (scheme and host only),
and the links keep the whole URL. With no path, nothing changes.

Run with pytest, or directly:
    uv run python tests/auth/test_instance_path.py
"""

import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("ALTCHA_HMAC_KEY", "test-altcha-hmac-key")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import backend.auth.totp as auth_totp  # noqa: E402
import backend.main as main  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.dependencies import require_admin, require_user  # noqa: E402
from backend.auth.middleware import anonymous_middleware  # noqa: E402
from backend.config import settings  # noqa: E402

WITH_PATH = "https://arena.example.test/fr"
NO_PATH = "https://arena.example.test"
PATH_CASES = [(WITH_PATH, "/fr"), (NO_PATH, "/")]


@contextlib.contextmanager
def public_url(url, **other):
    names = {"COMPARIA_APP_URL": url, **other}
    originals = {name: getattr(settings, name) for name in names}
    for name, value in names.items():
        setattr(settings, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(settings, name, value)


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def client_for(*, anonymous=False, user=None):
    app = FastAPI()
    app.include_router(auth_router.router)
    if anonymous:
        app.middleware("http")(anonymous_middleware)
    if user is not None:
        app.dependency_overrides[require_user] = lambda: user
    return TestClient(app, base_url="https://arena.example.test")


def cookie_named(response, name):
    [cookie] = [
        c for c in response.headers.get_list("set-cookie") if c.startswith(f"{name}=")
    ]
    return cookie


def path_of(cookie):
    [path] = [
        part.strip()[len("Path=") :]
        for part in cookie.split(";")
        if part.strip().lower().startswith("path=")
    ]
    return path


class NoRedis:
    def get(self, _key):
        return None

    def delete(self, _key):
        pass


async def email_code_enabled():
    return SimpleNamespace(auth_methods=["email_code"])


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_the_anonymous_session_cookie_uses_the_instance_path(url, expected):
    app = FastAPI()
    app.middleware("http")(anonymous_middleware)

    @app.get("/anything")
    async def anything() -> dict:
        return {}

    with public_url(url):
        response = TestClient(app).get("/anything")

    assert path_of(cookie_named(response, "anonymous_session")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_a_session_cookie_uses_the_instance_path(url, expected):
    async def signed_in(**_kwargs):
        return auth_services.LoginResult("session", "session-token")

    async def no_user(_token):
        return None

    with (
        public_url(url),
        patched(
            auth_router,
            verify_login_code=signed_in,
            get_redis_client=NoRedis,
            get_app_settings=email_code_enabled,
            get_user_from_token=no_user,
        ),
    ):
        response = client_for().post(
            "/auth/email/verify", json={"email": "a@example.org", "code": "123456"}
        )

    assert response.status_code == 200
    assert path_of(cookie_named(response, "auth_session")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_a_second_factor_challenge_cookie_uses_the_instance_path(url, expected):
    async def challenged(**_kwargs):
        return auth_services.LoginResult("totp_challenge", "challenge-token")

    with (
        public_url(url),
        patched(
            auth_router,
            verify_login_code=challenged,
            get_redis_client=NoRedis,
            get_app_settings=email_code_enabled,
        ),
    ):
        response = client_for().post(
            "/auth/email/verify", json={"email": "a@example.org", "code": "123456"}
        )

    assert response.status_code == 200
    # The challenge is set, and the session left over from another account is
    # deleted: both have to hit the cookie the browser actually holds.
    assert path_of(cookie_named(response, "auth_totp_challenge")) == expected
    assert path_of(cookie_named(response, "auth_session")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_an_expired_second_factor_deletes_the_challenge_on_the_instance_path(
    url, expected
):
    async def expired(**_kwargs):
        raise auth_totp.TotpChallengeExpiredError()

    with public_url(url), patched(auth_router, verify_totp_challenge=expired):
        client = client_for()
        client.cookies.set("auth_totp_challenge", "challenge-token")
        response = client.post("/auth/totp/verify", json={"code": "000000"})

    assert response.status_code == 410
    assert path_of(cookie_named(response, "auth_totp_challenge")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_a_finished_second_factor_swaps_its_cookies_on_the_instance_path(url, expected):
    async def accepted(**_kwargs):
        return "session-token"

    async def no_user(_token):
        return None

    with (
        public_url(url),
        patched(
            auth_router, verify_totp_challenge=accepted, get_user_from_token=no_user
        ),
    ):
        client = client_for()
        client.cookies.set("auth_totp_challenge", "challenge-token")
        response = client.post("/auth/totp/verify", json={"code": "123456"})

    assert response.status_code == 200
    assert path_of(cookie_named(response, "auth_totp_challenge")) == expected
    assert path_of(cookie_named(response, "auth_session")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_logout_deletes_both_cookies_on_the_instance_path(url, expected):
    with public_url(url):
        response = client_for().post("/auth/logout")

    assert response.status_code == 204
    assert path_of(cookie_named(response, "auth_session")) == expected
    assert path_of(cookie_named(response, "auth_totp_challenge")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_logout_everywhere_deletes_the_session_on_the_instance_path(url, expected):
    with public_url(url):
        response = client_for().post("/auth/logout-all")

    assert response.status_code == 204
    assert path_of(cookie_named(response, "auth_session")) == expected


@pytest.mark.parametrize(("url", "expected"), PATH_CASES)
def test_erasing_the_account_deletes_the_session_on_the_instance_path(url, expected):
    async def erased(_user_id):
        return None

    user = SimpleNamespace(id="u", email="a@example.org")
    with public_url(url), patched(auth_router, erase_user_account=erased):
        response = client_for(user=user).request(
            "DELETE", "/auth/me", json={"email": "a@example.org"}
        )

    assert response.status_code == 204
    assert path_of(cookie_named(response, "auth_session")) == expected


def oidc_client():
    async def get_app_settings():
        return SimpleNamespace(
            oidc_issuer="https://idp.example.test",
            oidc_client_id="client",
            oidc_scopes=["openid"],
        )

    async def discover(_issuer):
        return {"authorization_endpoint": "https://idp.example.test/authorize"}

    async def terms_accepted(**_kwargs):
        return True

    return patched(
        auth_router,
        get_app_settings=get_app_settings,
        oidc_available=lambda _settings: True,
        discover_provider=discover,
        build_authorization_url=lambda **_kwargs: (
            "https://idp.example.test/authorize?state=abc",
            "abc",
        ),
        has_current_terms_acceptance=terms_accepted,
        get_redis_client=lambda: SimpleNamespace(
            incr=lambda _key: 1, expire=lambda *_args: None
        ),
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [(WITH_PATH, "/fr/api/auth/oidc"), (NO_PATH, "/api/auth/oidc")],
)
def test_the_oidc_state_cookie_stays_on_the_callback_path_the_browser_sees(
    url, expected
):
    # Behind the Gateway the browser calls /fr/api/auth/oidc/callback, so a
    # cookie scoped to /api/auth/oidc would never come back.
    with public_url(url, COMPARIA_API_URL=None), oidc_client():
        client = client_for(anonymous=True)
        client.cookies.set("anonymous_session", "token")
        response = client.get("/auth/oidc/login", follow_redirects=False)
        spent = client.get(
            "/auth/oidc/callback?error=access_denied", follow_redirects=False
        )

    assert response.status_code == 302
    assert path_of(cookie_named(response, "oidc_state")) == expected
    assert path_of(cookie_named(spent, "oidc_state")) == expected


@pytest.mark.parametrize(
    ("origin", "status"),
    [
        ("https://arena.example.test", 401),
        ("https://arena.example.test/", 401),
        ("https://other.example.test", 403),
        ("http://arena.example.test", 403),
        # The browser never sends a path in Origin: one that does is not ours.
        ("https://arena.example.test/fr", 403),
    ],
)
def test_the_origin_check_accepts_the_origin_of_a_url_with_a_path(origin, status):
    # With no challenge cookie the handler answers 401 once the origin passed.
    with public_url(WITH_PATH):
        response = client_for().post(
            "/auth/totp/verify",
            json={"code": "123456"},
            headers={"origin": origin},
        )

    assert response.status_code == status


@pytest.mark.parametrize(
    ("origin", "status"),
    [("https://arena.example.test", 401), ("https://other.example.test", 403)],
)
def test_the_origin_check_is_unchanged_without_a_path(origin, status):
    with public_url(NO_PATH):
        response = client_for().post(
            "/auth/totp/verify",
            json={"code": "123456"},
            headers={"origin": origin},
        )

    assert response.status_code == status


def preflight(url, origin):
    with public_url(url):
        app = FastAPI()
        main.install_cors(app)
        return TestClient(app).options(
            "/anything",
            headers={
                "origin": origin,
                "access-control-request-method": "POST",
            },
        )


@pytest.mark.parametrize("url", [WITH_PATH, NO_PATH])
def test_cors_allows_the_origin_of_the_public_url(url):
    response = preflight(url, "https://arena.example.test")

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://arena.example.test"
    )
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize("url", [WITH_PATH, NO_PATH])
def test_cors_rejects_other_origins(url):
    response = preflight(url, "https://other.example.test")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_does_not_take_the_path_for_an_origin():
    response = preflight(WITH_PATH, "https://arena.example.test/fr")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_invitation_links_keep_the_instance_path():
    from backend.admin import router as admin_router

    sent = []

    async def create_invite(_email, invited_by):
        return "invite-token"

    async def send_invite_link(email, link, **_kwargs):
        sent.append(link)

    async def get_app_settings():
        return SimpleNamespace(
            platform_name="Arène de test",
            primary_color_light="#000091",
            secondary_color_light="#6A6AF4",
            default_locale="fr",
        )

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="admin")
    with (
        public_url(WITH_PATH),
        patched(
            admin_router,
            create_invite=create_invite,
            send_invite_link=send_invite_link,
            get_app_settings=get_app_settings,
        ),
    ):
        response = TestClient(app).post(
            "/admin/users/invite", json={"email": "new@example.org"}
        )

    assert response.status_code == 204
    assert sent == [f"{WITH_PATH}/invite/invite-token"]


def test_the_oidc_callback_url_and_login_redirects_keep_the_instance_path():
    from backend.auth.oidc import callback_origin, oidc_callback_url

    with public_url(WITH_PATH, COMPARIA_API_URL=None):
        assert oidc_callback_url() == f"{WITH_PATH}/api/auth/oidc/callback"
        assert callback_origin() == "https://arena.example.test"
        response = auth_router._login_error("provider_error")

    assert response.headers["location"] == f"{WITH_PATH}/login?error=provider_error"


def test_the_platform_url_keeps_the_instance_path():
    async def get_app_settings():
        return SimpleNamespace(
            auth_access_policy="anonymous_first",
            auth_methods=["email_code"],
            auth_domain_allowlist=[],
            oidc_issuer=None,
            oidc_client_id=None,
            oidc_client_secret_encrypted=None,
            oidc_scopes=["openid"],
            oidc_button_label=None,
            oidc_button_logo=None,
            platform_name="Arène de test",
            primary_color_light="#000091",
            primary_color_dark="#8585F6",
            secondary_color_light="#6A6AF4",
            secondary_color_dark="#CACAFB",
            homepage_url=None,
            logo=None,
            logo_version=None,
            enabled_locales=["fr"],
            default_locale="fr",
        )

    import asyncio

    with public_url(WITH_PATH), patched(auth_router, get_app_settings=get_app_settings):
        config = asyncio.run(auth_router.get_config())

    assert config.platform_url == WITH_PATH


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
