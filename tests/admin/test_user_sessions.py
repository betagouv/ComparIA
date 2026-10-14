"""
A session or link from before a role or address change must not act after it.

Driven through the HTTP API against a throwaway PostgreSQL (skipped where none
is installed): an account signs in, an admin changes it from the panel, and
the session it held before is what the tests look at.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from tests.auth.test_deleted_account import api, signed_in_as  # noqa: E402
from tests.auth.test_email_identity import (  # noqa: E402
    instance,
    sign_in_with_email_code,
)
from utils.database.models.auth import User  # noqa: E402
from utils.database.session import get_session  # noqa: E402


async def add_users(*users: User) -> None:
    async with get_session() as session:
        for user in users:
            session.add(user)
        await session.commit()
        for user in users:
            await session.refresh(user)


def test_a_session_from_before_a_promotion_cannot_enrol_an_authenticator(database):
    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        jean = User(email="jean@example.org")
        await add_users(boss, jean)

        with instance() as outbox:
            async with api() as old, api(boss) as panel:
                await sign_in_with_email_code(old, outbox, jean.email)
                response = await panel.put(
                    f"/admin/users/{jean.id}",
                    json={"email": jean.email, "role": "admin"},
                )
                assert response.status_code == 200, response.text

                assert await signed_in_as(old) is None
                response = await old.post("/auth/totp/setup", json={})
                assert response.status_code == 401, response.text

    database(scenario)


def test_a_session_from_before_a_demotion_is_closed(database):
    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        jean = User(email="jean@example.org", role="admin")
        await add_users(boss, jean)

        with instance() as outbox:
            async with api() as old, api(boss) as panel:
                await sign_in_with_email_code(old, outbox, jean.email)
                response = await panel.put(
                    f"/admin/users/{jean.id}",
                    json={"email": jean.email, "role": "user"},
                )
                assert response.status_code == 200, response.text

                assert await signed_in_as(old) is None

    database(scenario)


def test_an_edit_that_keeps_the_role_keeps_the_session(database):
    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        jean = User(email="jean@example.org")
        await add_users(boss, jean)

        with instance() as outbox:
            async with api() as old, api(boss) as panel:
                await sign_in_with_email_code(old, outbox, jean.email)
                response = await panel.put(
                    f"/admin/users/{jean.id}",
                    json={"email": jean.email, "role": "user"},
                )
                assert response.status_code == 200, response.text

                assert await signed_in_as(old) == {
                    "email": jean.email,
                    "role": "user",
                    "totp_enabled": False,
                    "questionsAnswered": True,
                }

    database(scenario)


async def invite(panel, outbox, email) -> str:
    response = await panel.post("/admin/users/invite", json={"email": email})
    assert response.status_code == 204, response.text
    _sent_to, link = outbox["invites"][-1]
    return link.rsplit("/", 1)[-1]


def test_promoting_an_invited_user_keeps_their_invite(database):
    """The panel only invites plain users, so an admin is added by inviting
    them and then changing the role: the link must still work after."""

    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        await add_users(boss)

        with instance() as outbox:
            async with api() as invited, api(boss) as panel:
                token = await invite(panel, outbox, "jean@example.org")
                users = await panel.get("/admin/users")
                [jean] = [
                    user
                    for user in users.json()["items"]
                    if user["email"] == "jean@example.org"
                ]
                response = await panel.put(
                    f"/admin/users/{jean['id']}",
                    json={"email": jean["email"], "role": "admin"},
                )
                assert response.status_code == 200, response.text

                response = await invited.post(
                    "/auth/invite/accept", json={"token": token}
                )
                assert response.status_code == 200, response.text
                assert (await signed_in_as(invited))["role"] == "admin"

    database(scenario)


def test_correcting_an_invited_address_cancels_the_link_sent_to_the_old_one(
    database,
):
    """The first link went to whoever reads the mistyped address. It must not
    open the account once the address is put right."""

    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        await add_users(boss)

        with instance() as outbox:
            async with api() as stranger, api(boss) as panel:
                token = await invite(panel, outbox, "jean@exmaple.org")
                users = await panel.get("/admin/users")
                [jean] = [
                    user
                    for user in users.json()["items"]
                    if user["email"] == "jean@exmaple.org"
                ]
                response = await panel.put(
                    f"/admin/users/{jean['id']}",
                    json={"email": "jean@example.org", "role": "user"},
                )
                assert response.status_code == 200, response.text

                response = await stranger.post(
                    "/auth/invite/accept", json={"token": token}
                )
                assert response.status_code != 200, response.text
                assert await signed_in_as(stranger) is None

    database(scenario)


def test_correcting_an_address_closes_the_sessions_opened_with_the_old_one(
    database,
):
    async def scenario():
        boss = User(email="boss@example.org", role="admin")
        jean = User(email="jean@exmaple.org")
        await add_users(boss, jean)

        with instance() as outbox:
            async with api() as old, api(boss) as panel:
                await sign_in_with_email_code(old, outbox, jean.email)
                response = await panel.put(
                    f"/admin/users/{jean.id}",
                    json={"email": "jean@example.org", "role": "user"},
                )
                assert response.status_code == 200, response.text

                assert await signed_in_as(old) is None

    database(scenario)
