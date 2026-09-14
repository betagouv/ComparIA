import uuid
from datetime import datetime

from sqlalchemy import update as sa_update
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.auth.services import drop_user_totp
from utils.database.models.auth import (
    AuthSession,
    InviteToken,
    LoginCode,
    User,
    UserPublic,
    UserTotp,
    UserUpsert,
)
from utils.database.models.utils import escape_like
from utils.database.session import get_session


class CannotDeleteSelfError(Exception):
    pass


class CannotDeleteLastAdminError(Exception):
    pass


class CannotDemoteLastAdminError(Exception):
    pass


class EmailAlreadyExistsError(Exception):
    pass


class CannotResetOwnTotpError(Exception):
    """Change your own device from the account page, with a code from the
    current one; the reset is for an admin who has lost theirs."""


async def _user_source(session: AsyncSession, user_id: uuid.UUID) -> str:
    invites_result = await session.exec(
        select(InviteToken).where(InviteToken.user_id == user_id)
    )
    invites = invites_result.all()
    codes_result = await session.exec(
        select(LoginCode).where(LoginCode.user_id == user_id)
    )
    codes = codes_result.all()
    if any(invite.used_at for invite in invites):
        return "email_invitation"
    elif any(code.used_at for code in codes):
        return "email_code"
    elif invites:
        return "pending_invite"
    elif codes:
        return "unknown"
    else:
        return "added_manually"


async def _enrolled_user_ids(
    session: AsyncSession, user_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    if not user_ids:
        return set()
    result = await session.exec(
        select(UserTotp.user_id).where(
            col(UserTotp.user_id).in_(user_ids), UserTotp.confirmed_at.is_not(None)
        )
    )
    return set(result.all())


def _to_user_public(user: User, source: str, totp_enabled: bool) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
        last_seen_at=user.last_seen_at.isoformat(),
        source=source,
        totp_enabled=totp_enabled,
    )


async def _user_public(session: AsyncSession, user: User) -> UserPublic:
    return _to_user_public(
        user,
        await _user_source(session, user.id),
        bool(await _enrolled_user_ids(session, [user.id])),
    )


async def list_users(
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[UserPublic], int]:
    async with get_session() as session:
        base = select(User).where(User.deleted_at.is_(None))
        if search:
            base = base.where(
                col(User.email).ilike(f"%{escape_like(search)}%", escape="\\")
            )

        count_result = await session.exec(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.one()

        result = await session.exec(
            base.order_by(col(User.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        users = result.all()

        enrolled = await _enrolled_user_ids(session, [user.id for user in users])
        rows = [
            _to_user_public(
                user, await _user_source(session, user.id), user.id in enrolled
            )
            for user in users
        ]

        return rows, total


async def create_user(data: UserUpsert) -> UserPublic:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == data.email))
        existing = result.first()

        if existing and existing.deleted_at is None:
            raise EmailAlreadyExistsError()

        if existing:
            existing.deleted_at = None
            existing.role = data.role
            user = existing
        else:
            user = User(email=data.email, role=data.role)

        session.add(user)
        await session.commit()
        await session.refresh(user)
        return await _user_public(session, user)


async def get_user(user_id: uuid.UUID) -> UserPublic | None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return None
        return await _user_public(session, user)


async def update_user(user_id: uuid.UUID, data: UserUpsert) -> UserPublic | None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return None

        if user.role == "admin" and data.role != "admin":
            other_admins = await session.exec(
                select(func.count()).select_from(
                    select(User)
                    .where(
                        col(User.role) == "admin",
                        User.deleted_at.is_(None),
                        User.id != user.id,
                    )
                    .subquery()
                )
            )
            if other_admins.one() == 0:
                raise CannotDemoteLastAdminError()
            # A plain user has no way to change or drop an authenticator, so
            # a demoted admin must not keep being challenged for one.
            await drop_user_totp(session, user.id)

        user.sqlmodel_update(data.model_dump(exclude={"id"}))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return await _user_public(session, user)


async def cancel_user_invite(user_id: uuid.UUID) -> bool:
    async with get_session() as session:
        result = await session.exec(
            select(InviteToken).where(
                InviteToken.user_id == user_id,
                InviteToken.used_at.is_(None),
            )
        )
        invites = result.all()
        if not invites:
            return False

        for invite in invites:
            await session.delete(invite)

        user = await session.get(User, user_id)
        if user:
            user.deleted_at = datetime.now()
            session.add(user)
        await drop_user_totp(session, user_id)

        await session.commit()
        return True


async def delete_user(user_id: uuid.UUID, current_user_id: uuid.UUID) -> bool:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return False

        if user.id == current_user_id:
            raise CannotDeleteSelfError()

        if user.role == "admin":
            other_admins = await session.exec(
                select(func.count()).select_from(
                    select(User)
                    .where(
                        col(User.role) == "admin",
                        User.deleted_at.is_(None),
                        User.id != user.id,
                    )
                    .subquery()
                )
            )
            if other_admins.one() == 0:
                raise CannotDeleteLastAdminError()

        # Soft-deleted accounts get revived by a later invite or manual add,
        # and must not come back tied to an old authenticator.
        await drop_user_totp(session, user_id)
        user.deleted_at = datetime.now()
        session.add(user)
        await session.commit()
        return True


async def reset_user_totp(user_id: uuid.UUID, current_user_id: uuid.UUID) -> bool:
    """Forget another admin's authenticator so they can enrol a new one at
    their next sign-in. Their sessions go with it: whoever holds one could
    otherwise enrol their own device first."""
    if user_id == current_user_id:
        raise CannotResetOwnTotpError()

    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return False
        if not await _enrolled_user_ids(session, [user_id]):
            return False

        await drop_user_totp(session, user_id)
        await session.execute(
            sa_update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now())
        )
        await session.commit()
        return True
