import logging

from sqlmodel import select

from backend.auth.services import drop_user_totp, revoke_user_access
from utils.database.models.auth import User
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


class UserNotFoundError(Exception):
    pass


async def reset_totp(email: str) -> None:
    """Forget an admin's authenticator and sign them out everywhere, for the
    case the admin panel cannot cover: the only admin has lost their phone.
    Their next sign-in takes an email code alone, then asks them to enrol."""
    async with get_session() as session:
        result = await session.exec(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.first()
        if user is None:
            raise UserNotFoundError(f"no account with email {email}")

        # Commit expires the row's attributes, so read the id before.
        user_id = user.id
        await drop_user_totp(session, user_id)
        await revoke_user_access(session, user_id)
        await session.commit()
    logger.warning(f"[AUTH] TOTP reset for user {user_id} by cli")
