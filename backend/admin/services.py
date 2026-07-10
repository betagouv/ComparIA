import uuid
from datetime import datetime

from sqlmodel import col, func, select

from utils.database.models.auth import InviteToken, LoginCode, User, UserPublic
from utils.database.session import get_session


class CannotDeleteSelfError(Exception):
    pass


class CannotDeleteLastAdminError(Exception):
    pass


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

        rows = []
        for user in users:
            invites_result = await session.exec(
                select(InviteToken).where(InviteToken.user_id == user.id)
            )
            invites = invites_result.all()
            used_code = await session.exec(
                select(LoginCode).where(
                    LoginCode.user_id == user.id,
                    LoginCode.used_at.is_not(None),
                )
            )
            if any(invite.used_at for invite in invites):
                source = "email_invitation"
            elif used_code.first():
                source = "email_code"
            elif invites:
                source = "pending_invite"
            else:
                source = "unknown"
            rows.append(
                UserPublic(
                    id=user.id,
                    email=user.email,
                    role=user.role,
                    created_at=user.created_at.isoformat(),
                    last_seen_at=user.last_seen_at.isoformat(),
                    source=source,
                )
            )

        return rows, total


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


async def set_user_role(user_id: uuid.UUID, role: str) -> User | None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return None
        user.role = role
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


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
