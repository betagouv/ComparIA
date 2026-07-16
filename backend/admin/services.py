import uuid
from datetime import datetime

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.database.models.auth import (
    InviteToken,
    LoginCode,
    User,
    UserPublic,
    UserUpsert,
)
from utils.database.session import get_session


class CannotDeleteSelfError(Exception):
    pass


class CannotDeleteLastAdminError(Exception):
    pass


class EmailAlreadyExistsError(Exception):
    pass


async def _user_source(session: AsyncSession, user_id: uuid.UUID) -> str:
    invites_result = await session.exec(
        select(InviteToken).where(InviteToken.user_id == user_id)
    )
    invites = invites_result.all()
    used_code = await session.exec(
        select(LoginCode).where(
            LoginCode.user_id == user_id,
            LoginCode.used_at.is_not(None),
        )
    )
    if any(invite.used_at for invite in invites):
        return "email_invitation"
    elif used_code.first():
        return "email_code"
    elif invites:
        return "pending_invite"
    else:
        return "unknown"


def _to_user_public(user: User, source: str) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
        last_seen_at=user.last_seen_at.isoformat(),
        source=source,
    )


async def list_users(
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[UserPublic], int]:
    async with get_session() as session:
        base = select(User).where(User.deleted_at.is_(None))
        if search:
            base = base.where(col(User.email).ilike(f"%{search}%"))

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

        rows = [
            _to_user_public(user, await _user_source(session, user.id))
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
        return _to_user_public(user, await _user_source(session, user.id))


async def get_user(user_id: uuid.UUID) -> UserPublic | None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return None
        return _to_user_public(user, await _user_source(session, user.id))


async def update_user(user_id: uuid.UUID, data: UserUpsert) -> UserPublic | None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return None
        user.sqlmodel_update(data.model_dump(exclude={"id"}))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return _to_user_public(user, await _user_source(session, user.id))


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

        user.deleted_at = datetime.now()
        session.add(user)
        await session.commit()
        return True
