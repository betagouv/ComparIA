import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import update as sa_update
from sqlmodel import select

from backend.config import settings
from utils.database.models.auth import (
    AuthSession,
    ConsentLog,
    InviteToken,
    LoginCode,
    User,
)
from utils.database.models.comparison import Comparison
from utils.database.session import get_session

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger("languia")

_LOGIN_CODE_TTL_MINUTES = 10
_INVITE_TOKEN_TTL_HOURS = 24


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def request_login_code(email: str) -> str:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            user = User(email=email)
            session.add(user)
            await session.flush()

        await session.execute(
            sa_update(LoginCode)
            .where(LoginCode.user_id == user.id, LoginCode.used_at.is_(None))
            .values(used_at=datetime.now())
        )

        code = f"{secrets.randbelow(10**6):06d}"
        session.add(
            LoginCode(
                user_id=user.id,
                code_hash=_hash(code),
                expires_at=datetime.now() + timedelta(minutes=_LOGIN_CODE_TTL_MINUTES),
            )
        )
        await session.commit()

    return code


async def _create_session_and_consent(
    session: "AsyncSession",
    user: User,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
) -> str:
    """Create the AuthSession + ConsentLog for a user that just authenticated
    (login code or invite link), and reattach their anonymous comparisons.
    Does not commit; caller owns the transaction."""
    user.last_seen_at = datetime.now()

    token = secrets.token_urlsafe(32)
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=datetime.now()
            + timedelta(days=settings.AUTH_SESSION_LENGTH_DAYS),
            ip=ip,
            user_agent=user_agent,
        )
    )
    session.add(
        ConsentLog(
            user_id=user.id,
            terms_version=settings.AUTH_TERMS_VERSION,
            ip=ip,
        )
    )

    if visitor_id:
        await session.execute(
            sa_update(Comparison)
            .where(
                Comparison.visitor_id == visitor_id,
                Comparison.user_id.is_(None),
            )
            .values(user_id=user.id)
        )

    return token


async def verify_login_code(
    email: str,
    code: str,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
) -> str | None:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            return None

        result = await session.exec(
            select(LoginCode).where(
                LoginCode.user_id == user.id,
                LoginCode.code_hash == _hash(code),
                LoginCode.used_at.is_(None),
                LoginCode.expires_at > datetime.now(),
            )
        )
        login_code = result.first()
        if not login_code:
            return None

        login_code.used_at = datetime.now()

        token = await _create_session_and_consent(
            session, user, ip, user_agent, visitor_id
        )

        await session.commit()

    return token


async def create_invite(email: str, invited_by: uuid.UUID) -> str:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            user = User(email=email)
            session.add(user)
            await session.flush()

        token = secrets.token_urlsafe(32)
        session.add(
            InviteToken(
                user_id=user.id,
                invited_by=invited_by,
                token_hash=_hash(token),
                expires_at=datetime.now() + timedelta(hours=_INVITE_TOKEN_TTL_HOURS),
            )
        )
        await session.commit()

    return token


@dataclass
class InviteTokenInfo:
    email: str


async def get_invite_token_info(token: str) -> InviteTokenInfo | None:
    """Read-only check used by the frontend to show an error before the user
    even fills in the consent form. Does not mark the token as used — the
    actual accept_invite() call re-validates everything regardless."""
    async with get_session() as session:
        result = await session.exec(
            select(InviteToken).where(
                InviteToken.token_hash == _hash(token),
                InviteToken.used_at.is_(None),
                InviteToken.expires_at > datetime.now(),
            )
        )
        invite = result.first()
        if not invite:
            return None

        user = await session.get(User, invite.user_id)
        if not user or user.deleted_at is not None:
            return None

        return InviteTokenInfo(email=user.email)


async def accept_invite(
    token: str,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
) -> str | None:
    async with get_session() as session:
        result = await session.exec(
            select(InviteToken).where(
                InviteToken.token_hash == _hash(token),
                InviteToken.used_at.is_(None),
                InviteToken.expires_at > datetime.now(),
            )
        )
        invite = result.first()
        if not invite:
            return None

        user = await session.get(User, invite.user_id)
        if not user or user.deleted_at is not None:
            return None

        invite.used_at = datetime.now()

        session_token = await _create_session_and_consent(
            session, user, ip, user_agent, visitor_id
        )

        await session.commit()

    return session_token


async def get_user_from_token(token: str) -> User | None:
    async with get_session() as session:
        result = await session.exec(
            select(AuthSession).where(
                AuthSession.token_hash == _hash(token),
                AuthSession.expires_at > datetime.now(),
                AuthSession.revoked_at.is_(None),
            )
        )
        auth_session = result.first()
        if not auth_session:
            return None

        user = await session.get(User, auth_session.user_id)
        if not user or user.deleted_at is not None:
            return None

        return user


async def revoke_current_session(token: str) -> None:
    async with get_session() as session:
        result = await session.exec(
            select(AuthSession).where(AuthSession.token_hash == _hash(token))
        )
        auth_session = result.first()
        if auth_session:
            auth_session.revoked_at = datetime.now()
            session.add(auth_session)
            await session.commit()


async def revoke_all_user_sessions(user_id: uuid.UUID) -> None:
    async with get_session() as session:
        await session.execute(
            sa_update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now())
        )
        await session.commit()
