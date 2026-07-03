import logging

from sqlmodel import select

from backend.config import settings
from utils.database.models.auth import User
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


async def seed_admins() -> None:
    """Upsert admin role for emails listed in ADMIN_EMAILS setting."""
    if not settings.ADMIN_EMAILS:
        logger.info("[seed] ADMIN_EMAILS is empty, nothing to do")
        return

    if not settings.COMPARIA_DB_URI:
        logger.warning("[seed] COMPARIA_DB_URI is not set, skipping seed_admins")
        return

    async with get_session() as session:
        for email in settings.ADMIN_EMAILS:
            result = await session.exec(select(User).where(User.email == email))
            user = result.first()
            if user:
                if user.role != "admin":
                    user.role = "admin"
                    session.add(user)
                    logger.info(f"[seed] promoted {email} to admin")
                else:
                    logger.info(f"[seed] {email} is already admin")
            else:
                session.add(User(email=email, role="admin"))
                logger.info(f"[seed] created admin user {email}")
        await session.commit()
