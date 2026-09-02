import logging

from sqlmodel import select

from backend.config import settings
from utils.database.models.auth import User
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


async def seed_admins() -> None:
    """Create the accounts listed in ADMIN_EMAILS, once, as admins."""
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
            if user is None:
                session.add(User(email=email, role="admin"))
                logger.warning(f"[seed] created admin user {email}")
            elif user.role != "admin":
                # Promoting on every boot would undo a demotion made in the admin
                # panel, and would hand admin to whoever signed up with a listed
                # address meanwhile. Change the role there, not by restarting.
                logger.warning(
                    f"[seed] {email} already exists with role '{user.role}', left as is"
                )
            else:
                logger.info(f"[seed] {email} is already admin")
        await session.commit()
