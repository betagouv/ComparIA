"""
A deleted account has no way back in until an admin brings it back, and comes
back with nothing it held before.

Driven through the HTTP API against a throwaway PostgreSQL (skipped where none
is installed).
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from sqlmodel import select  # noqa: E402

from backend.auth.services import _hash  # noqa: E402
from tests.auth import test_email_identity  # noqa: E402
from tests.auth.test_email_identity import instance  # noqa: E402
from utils.database.models.auth import (  # noqa: E402
    AuthSession,
    LoginCode,
    User,
    UserTotp,
)
from utils.database.session import get_session  # noqa: E402


def api(admin: User | None = None):
    """Over https, or the client keeps the session cookie to itself."""
    client = test_email_identity.api(admin)
    client.base_url = "https://backend"
    return client


async def add_deleted(email: str, role: str = "user") -> User:
    user = User(email=email, role=role, deleted_at=datetime.now())
    async with get_session() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def rows(model, user_id):
    async with get_session() as session:
        result = await session.exec(select(model).where(model.user_id == user_id))
        return result.all()


async def signed_in_as(client) -> dict | None:
    response = await client.get("/auth/me")
    assert response.status_code == 200, response.text
    return response.json()["user"]


def test_a_deleted_address_gets_no_code_and_the_same_answer_as_an_unknown_one(
    database,
):
    async def scenario():
        gone = await add_deleted("gone@example.org")

        with instance() as outbox:
            async with api() as client:
                deleted = await client.post(
                    "/auth/email/request",
                    json={"email": gone.email, "altcha_payload": "ok"},
                )
                unknown = await client.post(
                    "/auth/email/request",
                    json={"email": "new@example.org", "altcha_payload": "ok"},
                )

        assert (deleted.status_code, deleted.content) == (
            unknown.status_code,
            unknown.content,
        )
        assert deleted.status_code == 204
        assert [email for email, _code in outbox["codes"]] == ["new@example.org"]
        assert await rows(LoginCode, gone.id) == []

    database(scenario)


def test_a_deleted_account_cannot_sign_in_with_a_code(database):
    """A code issued before the fix, or left over some other way, must not
    open a session either."""

    async def scenario():
        gone = await add_deleted("gone@example.org")
        async with get_session() as session:
            session.add(
                LoginCode(
                    user_id=gone.id,
                    code_hash=_hash("123456"),
                    expires_at=datetime.now() + timedelta(minutes=10),
                )
            )
            await session.commit()

        with instance():
            async with api() as client:
                response = await client.post(
                    "/auth/email/verify",
                    json={"email": gone.email, "code": "123456"},
                )

        assert response.status_code == 400, response.text
        assert "auth_session" not in response.cookies
        assert await rows(AuthSession, gone.id) == []

    database(scenario)


def test_re_inviting_a_deleted_account_brings_back_no_session_role_or_authenticator(
    database,
):
    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        async with get_session() as session:
            session.add(boss)
            await session.commit()
            await session.refresh(boss)
        gone = await add_deleted("gone@example.org", role="admin")
        async with get_session() as session:
            session.add(
                AuthSession(
                    user_id=gone.id,
                    token_hash=_hash("stale"),
                    expires_at=datetime.now() + timedelta(days=30),
                    ip="127.0.0.1",
                )
            )
            session.add(
                UserTotp(
                    user_id=gone.id,
                    secret_encrypted="old",
                    confirmed_at=datetime.now(),
                )
            )
            await session.commit()

        with instance() as outbox:
            async with api() as old, api(boss) as panel:
                response = await panel.post(
                    "/admin/users/invite", json={"email": gone.email}
                )
                assert response.status_code == 204, response.text
                assert len(outbox["invites"]) == 1

                old.cookies.set("auth_session", "stale")
                assert await signed_in_as(old) is None

        async with get_session() as session:
            revived = await session.get(User, gone.id)
            assert revived is not None
            assert revived.deleted_at is None
            assert revived.role == "user"
        assert await rows(UserTotp, gone.id) == []

    database(scenario)


def test_re_adding_a_deleted_account_brings_back_no_session_or_authenticator(
    database,
):
    """Sessions left over from before the deletion, or opened while it lasted,
    must stay dead once an admin adds the address again."""

    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        async with get_session() as session:
            session.add(boss)
            await session.commit()
            await session.refresh(boss)
        gone = await add_deleted("gone@example.org")
        async with get_session() as session:
            session.add(
                AuthSession(
                    user_id=gone.id,
                    token_hash=_hash("stale"),
                    expires_at=datetime.now() + timedelta(days=30),
                    ip="127.0.0.1",
                )
            )
            session.add(
                UserTotp(
                    user_id=gone.id,
                    secret_encrypted="old",
                    confirmed_at=datetime.now(),
                )
            )
            await session.commit()

        with instance():
            async with api() as old, api(boss) as panel:
                response = await panel.post(
                    "/admin/users", json={"email": gone.email, "role": "admin"}
                )
                assert response.status_code == 201, response.text
                assert response.json()["totp_enabled"] is False

                old.cookies.set("auth_session", "stale")
                assert await signed_in_as(old) is None

        assert await rows(UserTotp, gone.id) == []

    database(scenario)
