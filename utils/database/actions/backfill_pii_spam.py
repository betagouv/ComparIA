import logging
from datetime import datetime

from sqlmodel import and_, col, update

from utils.database.models.comparison import Comparison
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


async def backfill_pii_spam(*, commit: bool = False) -> None:
    """
    Backfill archived fields for comparisons with contains_pii=TRUE or contains_spam=TRUE.
    Sets archived=TRUE, archived_reason='pii'|'spam', archived_at=now().
    Only affects comparisons where archived IS NOT TRUE.
    """
    now = datetime.now()

    async with get_session() as session:
        pii_query = (
            update(Comparison)
            .where(
                and_(
                    col(Comparison.contains_pii) == True,
                    col(Comparison.archived) != True,
                )
            )
            .values(archived=True, archived_reason="pii", archived_at=now)
        )
        pii_result = await session.execute(pii_query)

        spam_query = (
            update(Comparison)
            .where(
                and_(
                    col(Comparison.contains_spam) == True,
                    col(Comparison.archived) != True,
                )
            )
            .values(archived=True, archived_reason="spam", archived_at=now)
        )
        spam_result = await session.execute(spam_query)

        if commit:
            await session.commit()
            logger.info(
                f"Backfilled {pii_result.rowcount} pii and {spam_result.rowcount} spam comparisons."
            )
        else:
            logger.error(
                f"{pii_result.rowcount} pii and {spam_result.rowcount} spam comparisons should be archived (dry-run)."
            )
