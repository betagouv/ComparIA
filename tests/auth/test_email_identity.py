"""
One email, one account, whatever the letter case and the sign-in method.

Driven through the HTTP API against a throwaway PostgreSQL (skipped where none
is installed): the email code flow, the SSO callback and the admin invite all
meet the same `auth_user` table, and the point is what ends up in it.

Run with pytest.
"""

import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlmodel import select  # noqa: E402

import backend.admin.router as admin_router  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.dependencies import require_admin  # noqa: E402
from backend.auth.oidc import PendingLogin  # noqa: E402
from tests.auth.fake_oidc_provider import (  # noqa: E402
    CLIENT_ID,
    ENCRYPTED_CLIENT_SECRET,
    ISSUER,
    FakeProvider,
    serving,
)
from utils.database.models.auth import User  # noqa: E402
from utils.database.session import get_session  # noqa: E402


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


class FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, seconds):
        pass

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


def _settings_row():
    return SimpleNamespace(
        auth_access_policy="anonymous_first",
        auth_domain_allowlist=[],
        auth_methods=["email_code", "oidc"],
        oidc_issuer=ISSUER,
        oidc_client_id=CLIENT_ID,
        oidc_client_secret_encrypted=ENCRYPTED_CLIENT_SECRET,
        oidc_scopes=["openid", "email"],
        platform_name="Test",
        primary_color_light="#000091",
        secondary_color_light="#6A6AF4",
        default_locale="fr",
    )


@contextlib.contextmanager
def instance(provider=None):
    """The auth and admin routers on a fake instance: a fake provider, a
    recorded outbox, and the real database."""
    row = _settings_row()
    outbox: dict[str, list] = {"codes": [], "invites": []}

    async def get_app_settings():
        return row

    async def has_current_terms_acceptance(**_kwargs):
        return True

    async def send_login_code(email, code, **_kwargs):
        outbox["codes"].append((email, code))

    async def send_invite_link(email, link, **_kwargs):
        outbox["invites"].append((email, link))

    def consume_state(state):
        return PendingLogin(nonce="the-nonce", redirect="/", merge=False)

    redis = FakeRedis()
    with (
        serving(provider or FakeProvider()),
        patched(
            auth_router,
            get_app_settings=get_app_settings,
            has_current_terms_acceptance=has_current_terms_acceptance,
            send_login_code=send_login_code,
            verify_altcha_token=lambda _payload: (True, None),
            consume_state=consume_state,
            get_redis_client=lambda: redis,
        ),
        patched(
            admin_router,
            get_app_settings=get_app_settings,
            send_invite_link=send_invite_link,
        ),
    ):
        yield outbox


def api(admin: User | None = None) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(auth_router.router)
    app.include_router(admin_router.router)
    if admin is not None:
        app.dependency_overrides[require_admin] = lambda: admin
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://backend"
    )
    client.cookies.set("anonymous_session", "token")
    return client


async def sign_in_with_email_code(client, outbox, email):
    response = await client.post(
        "/auth/email/request", json={"email": email, "altcha_payload": "ok"}
    )
    assert response.status_code == 204, response.text
    _sent_to, code = outbox["codes"][-1]
    response = await client.post(
        "/auth/email/verify", json={"email": email, "code": code}
    )
    assert response.status_code == 200, response.text


async def sign_in_with_sso(client):
    client.cookies.set("oidc_state", "good-state")
    response = await client.get(
        "/auth/oidc/callback", params={"code": "auth-code", "state": "good-state"}
    )
    assert response.status_code == 302, response.text
    assert "error=" not in response.headers["location"], response.headers["location"]


def sso_provider(email):
    provider = FakeProvider()
    provider.userinfo_claims["email"] = email
    return provider


async def emails():
    async with get_session() as session:
        result = await session.exec(select(User.email))
        return sorted(result.all())


def test_sso_then_email_code_land_on_the_same_account_whatever_the_case(database):
    async def scenario():
        with instance(sso_provider("Jean.Dupont@Example.org")) as outbox:
            async with api() as client:
                await sign_in_with_sso(client)
                await sign_in_with_email_code(client, outbox, "jean.dupont@example.org")
        assert await emails() == ["jean.dupont@example.org"]

    database(scenario)


def test_email_code_then_sso_land_on_the_same_account_whatever_the_case(database):
    async def scenario():
        with instance(sso_provider("JEAN.DUPONT@example.org")) as outbox:
            async with api() as client:
                await sign_in_with_email_code(client, outbox, "Jean.Dupont@example.org")
                await sign_in_with_sso(client)
        assert await emails() == ["jean.dupont@example.org"]

    database(scenario)


def test_an_account_created_with_a_mixed_case_email_can_still_sign_in(database):
    """Accounts from before the fix keep their spelling until the migration
    rewrites it: the sign-in must find them either way."""

    async def scenario():
        async with get_session() as session:
            session.add(User(email="Jean.Dupont@example.org"))
            await session.commit()

        with instance(sso_provider("jean.dupont@example.org")) as outbox:
            async with api() as client:
                await sign_in_with_email_code(client, outbox, "jean.dupont@example.org")
                await sign_in_with_sso(client)
        assert await emails() == ["Jean.Dupont@example.org"]

    database(scenario)


def test_an_invite_reaches_the_existing_account_whatever_the_case(database):
    async def scenario():
        async with get_session() as session:
            admin = User(email="admin@example.org", role="admin")
            session.add(admin)
            session.add(User(email="jean.dupont@example.org"))
            await session.commit()
            await session.refresh(admin)

        with instance() as outbox:
            async with api(admin) as client:
                response = await client.post(
                    "/admin/users/invite", json={"email": "Jean.Dupont@Example.org"}
                )
        assert response.status_code == 204, response.text
        assert len(outbox["invites"]) == 1
        assert await emails() == ["admin@example.org", "jean.dupont@example.org"]

    database(scenario)


def test_two_spellings_of_one_address_cannot_be_stored_twice(database):
    async def scenario():
        async with get_session() as session:
            session.add(User(email="jean.dupont@example.org"))
            await session.commit()
        async with get_session() as session:
            session.add(User(email="Jean.Dupont@example.org"))
            try:
                await session.commit()
            except Exception:
                return
        raise AssertionError("the database accepted a second spelling of the address")

    database(scenario)


def test_the_configured_admins_are_seeded_lowercased_without_duplicates(database):
    from backend.config import settings
    from utils.database.actions.seed import seed_admins

    async def scenario():
        async with get_session() as session:
            session.add(User(email="boss@example.org", role="admin"))
            await session.commit()
        with patched(
            settings, ADMIN_EMAILS=["Boss@Example.org", "New.Admin@Example.org"]
        ):
            await seed_admins()
        assert await emails() == ["boss@example.org", "new.admin@example.org"]

    database(scenario)
