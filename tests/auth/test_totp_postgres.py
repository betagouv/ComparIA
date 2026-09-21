"""
Concurrency guarantees of the authenticator flow, against a real PostgreSQL.

The unit tests replay statements on a fake session, which says nothing about
row locks. These run only when COMPARIA_TEST_DB_URI points at a database that
can be wiped, e.g.:

    createdb comparia_test
    COMPARIA_TEST_DB_URI=postgresql://postgres@localhost:5432/comparia_test uv run pytest tests/auth/test_totp_postgres.py
"""

import asyncio
import contextlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pyotp  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel import SQLModel, select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

import backend.auth.services as auth_services  # noqa: E402
import backend.auth.totp as auth_totp  # noqa: E402
import utils.database.models  # noqa: E402,F401
from utils.database.models.auth import (  # noqa: E402
    AuthSession,
    TotpChallenge,
    User,
    UserTotp,
)
from utils.database.session import _async_url  # noqa: E402

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI")

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")


@contextlib.contextmanager
def real_database():
    engine = create_async_engine(_async_url(TEST_DB_URI), pool_size=12, max_overflow=0)

    @contextlib.asynccontextmanager
    async def get_session():
        async with AsyncSession(engine) as session:
            yield session

    # Only the auth tables: the whole metadata drags in the LLM catalogue.
    tables = [
        SQLModel.metadata.tables[name]
        for name in (
            "auth_user",
            "auth_session",
            "auth_login_code",
            "auth_invite_token",
            "auth_totp",
            "auth_totp_challenge",
        )
    ]

    async def reset_schema():
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: SQLModel.metadata.drop_all(c, tables=tables[::-1])
            )
            await conn.run_sync(
                lambda c: SQLModel.metadata.create_all(c, tables=tables)
            )

    asyncio.run(reset_schema())
    originals = (auth_totp.get_session, auth_services.get_session)
    auth_totp.get_session = auth_services.get_session = get_session
    try:
        yield get_session
    finally:
        auth_totp.get_session, auth_services.get_session = originals
        asyncio.run(engine.dispose())


async def enrolled_admin(get_session, secret):
    async with get_session() as session:
        user = User(email="admin@example.org", role="admin")
        session.add(user)
        await session.flush()
        user_id = user.id
        session.add(
            UserTotp(
                user_id=user.id,
                secret_encrypted=auth_totp.encrypt_secret(secret),
                confirmed_at=datetime.now(),
            )
        )
        session.add(
            TotpChallenge(
                user_id=user.id,
                token_hash=auth_services._hash("challenge-token"),
                expires_at=datetime.now() + timedelta(minutes=10),
            )
        )
        await session.commit()
        return user_id


async def attempt(code):
    try:
        await auth_totp.verify_totp_challenge(
            "challenge-token", code, "192.0.2.1", None, None
        )
        return "session"
    except auth_totp.InvalidTotpCodeError:
        return "invalid"
    except auth_totp.TotpChallengeExpiredError:
        return "expired"


async def count(get_session, model, *where):
    async with get_session() as session:
        result = await session.exec(select(model).where(*where))
        return len(result.all())


def test_concurrent_wrong_codes_all_count():
    secret = pyotp.random_base32()
    with real_database() as get_session:
        asyncio.run(enrolled_admin(get_session, secret))

        async def run():
            return await asyncio.gather(*(attempt("000000") for _ in range(10)))

        outcomes = asyncio.run(run())

        async def attempts():
            async with get_session() as session:
                return (await session.exec(select(TotpChallenge))).one().attempts

        assert asyncio.run(attempts()) == auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS
        assert outcomes.count("invalid") == auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS - 1
        assert outcomes.count("expired") == 10 - (
            auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS - 1
        )


def test_concurrent_right_codes_open_one_session():
    secret = pyotp.random_base32()
    with real_database() as get_session:
        asyncio.run(enrolled_admin(get_session, secret))
        code = pyotp.TOTP(secret).now()

        async def run():
            return await asyncio.gather(*(attempt(code) for _ in range(10)))

        outcomes = asyncio.run(run())
        assert outcomes.count("session") == 1
        assert asyncio.run(count(get_session, AuthSession)) == 1


def test_confirming_and_revoking_is_one_transaction():
    """If the revocation cannot be written, the confirmation is not either."""
    secret = pyotp.random_base32()
    with real_database() as get_session:

        async def setup():
            async with get_session() as session:
                user = User(email="admin@example.org", role="admin")
                session.add(user)
                await session.flush()
                for token in ("keep-me", "old-session"):
                    session.add(
                        AuthSession(
                            user_id=user.id,
                            token_hash=auth_services._hash(token),
                            expires_at=datetime.now() + timedelta(days=1),
                            ip="192.0.2.1",
                        )
                    )
                session.add(
                    UserTotp(
                        user_id=user.id,
                        pending_secret_encrypted=auth_totp.encrypt_secret(secret),
                        pending_created_at=datetime.now(),
                    )
                )
                await session.commit()
                await session.refresh(user)
                return user

        user = asyncio.run(setup())

        async def failing_revoke(*_args):
            raise RuntimeError("database went away")

        original = auth_totp._revoke_other_user_sessions
        auth_totp._revoke_other_user_sessions = failing_revoke
        try:
            with pytest.raises(RuntimeError):
                asyncio.run(
                    auth_totp.confirm_totp_setup(
                        user, pyotp.TOTP(secret).now(), "keep-me"
                    )
                )
        finally:
            auth_totp._revoke_other_user_sessions = original

        assert (
            asyncio.run(
                count(get_session, UserTotp, UserTotp.confirmed_at.is_not(None))
            )
            == 0
        )
        assert (
            asyncio.run(
                count(get_session, AuthSession, AuthSession.revoked_at.is_(None))
            )
            == 2
        )

        asyncio.run(
            auth_totp.confirm_totp_setup(user, pyotp.TOTP(secret).now(), "keep-me")
        )
        assert (
            asyncio.run(
                count(get_session, UserTotp, UserTotp.confirmed_at.is_not(None))
            )
            == 1
        )
        assert (
            asyncio.run(
                count(get_session, AuthSession, AuthSession.revoked_at.is_(None))
            )
            == 1
        )


async def spent_challenges(get_session, user_id, *attempt_counts, age=timedelta()):
    """Earlier challenges of the account, each used up with that many wrong
    codes, created `age` ago."""
    async with get_session() as session:
        for i, attempts in enumerate(attempt_counts):
            session.add(
                TotpChallenge(
                    user_id=user_id,
                    token_hash=auth_services._hash(f"spent-{age}-{i}"),
                    created_at=datetime.now() - age,
                    expires_at=datetime.now() - age + timedelta(minutes=10),
                    used_at=datetime.now() - age,
                    attempts=attempts,
                )
            )
        await session.commit()


def test_wrong_codes_are_capped_per_account_over_the_hour():
    """A new email code buys a new challenge: the cap has to span them."""
    secret = pyotp.random_base32()
    cap = auth_totp._TOTP_MAX_FAILS_PER_USER_PER_HOUR
    with real_database() as get_session:
        user_id = asyncio.run(enrolled_admin(get_session, secret))
        asyncio.run(spent_challenges(get_session, user_id, cap - 1))
        assert asyncio.run(attempt("000000")) == "invalid"
        # That one made it `cap`: the right code is refused from now on.
        assert asyncio.run(attempt(pyotp.TOTP(secret).now())) == "expired"
        assert asyncio.run(count(get_session, AuthSession)) == 0

    with real_database() as get_session:
        user_id = asyncio.run(enrolled_admin(get_session, secret))
        asyncio.run(spent_challenges(get_session, user_id, cap - 1))
        assert asyncio.run(attempt(pyotp.TOTP(secret).now())) == "session"
        assert asyncio.run(count(get_session, AuthSession)) == 1


def test_failures_older_than_an_hour_are_forgotten_and_pruned():
    secret = pyotp.random_base32()
    cap = auth_totp._TOTP_MAX_FAILS_PER_USER_PER_HOUR
    with real_database() as get_session:
        user_id = asyncio.run(enrolled_admin(get_session, secret))
        asyncio.run(
            spent_challenges(get_session, user_id, cap, cap, age=timedelta(hours=2))
        )
        asyncio.run(spent_challenges(get_session, user_id, 1))
        assert asyncio.run(count(get_session, TotpChallenge)) == 4

        assert asyncio.run(attempt(pyotp.TOTP(secret).now())) == "session"

        # The two old rows went with the sign-in; the recent one is still
        # counted, so it stays.
        assert asyncio.run(count(get_session, TotpChallenge)) == 2
        assert (
            asyncio.run(
                count(
                    get_session,
                    TotpChallenge,
                    TotpChallenge.created_at < datetime.now() - timedelta(hours=1),
                )
            )
            == 0
        )
