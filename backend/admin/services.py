import uuid
from datetime import datetime

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.auth.services import drop_user_totp, revoke_user_access
from utils.database.models.auth import (
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


def _source_of(
    has_used_invite: bool, has_used_code: bool, has_invite: bool, has_code: bool
) -> str:
    if has_used_invite:
        return "email_invitation"
    if has_used_code:
        return "email_code"
    if has_invite:
        return "pending_invite"
    if has_code:
        return "unknown"
    return "added_manually"


async def _user_sources(
    session: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """How each account came to exist, from its invite and login code
    history. Two grouped queries for the whole page, not two per user."""
    if not user_ids:
        return {}
    invites = await session.exec(
        select(InviteToken.user_id, func.bool_or(InviteToken.used_at.is_not(None)))
        .where(col(InviteToken.user_id).in_(user_ids))
        .group_by(InviteToken.user_id)
    )
    invited = dict(invites.all())
    codes = await session.exec(
        select(LoginCode.user_id, func.bool_or(LoginCode.used_at.is_not(None)))
        .where(col(LoginCode.user_id).in_(user_ids))
        .group_by(LoginCode.user_id)
    )
    coded = dict(codes.all())
    return {
        user_id: _source_of(
            bool(invited.get(user_id)),
            bool(coded.get(user_id)),
            user_id in invited,
            user_id in coded,
        )
        for user_id in user_ids
    }


async def _user_source(session: AsyncSession, user_id: uuid.UUID) -> str:
    return (await _user_sources(session, [user_id]))[user_id]


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

        user_ids = [user.id for user in users]
        enrolled = await _enrolled_user_ids(session, user_ids)
        sources = await _user_sources(session, user_ids)
        rows = [
            _to_user_public(user, sources[user.id], user.id in enrolled)
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
        await revoke_user_access(session, user_id)
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
        # and must not come back with an old session or authenticator.
        await revoke_user_access(session, user_id)
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
        await revoke_user_access(session, user_id)
        await session.commit()
        return True
