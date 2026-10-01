import logging

from sqlmodel import col, func, select, update

from utils.database.models.comparison import Comparison
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


async def clear_visitor_ids(*, commit: bool = False, batch_size: int = 10_000) -> None:
    """
    Blank the Matomo visitor id that comparisons used to keep, so audience
    data is no longer tied to arena conversations. Only counts the rows by
    default, set 'commit' to actually clear them.
    """
    has_visitor_id = col(Comparison.visitor_id).is_not(None)

    if not commit:
        async with get_session() as session:
            count = (
                await session.exec(
                    select(func.count(col(Comparison.id))).where(has_visitor_id)
                )
            ).one()
        logger.warning(f"{count} comparisons hold a visitor id (dry-run).")
        return

    # Short transactions, so no row stays locked for the whole run.
    cleared = 0
    while True:
        async with get_session() as session:
            batch = select(Comparison.id).where(has_visitor_id).limit(batch_size)
            result = await session.exec(
                update(Comparison)
                .where(col(Comparison.id).in_(batch.scalar_subquery()))
                .values(visitor_id=None)
            )
            await session.commit()
        if not result.rowcount:
            break
        cleared += result.rowcount
        logger.info(f"Cleared {cleared} visitor ids so far.")

    logger.warning(f"Cleared the visitor id of {cleared} comparisons.")
