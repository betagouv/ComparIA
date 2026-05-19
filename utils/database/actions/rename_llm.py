import logging

from sqlmodel import col, update

from ..models import Comparison
from ..session import get_session

logger = logging.getLogger("comparia.db")


async def rename_llm(old_name: str, new_name: str, *, commit: bool = False):
    """
    Rename an LLM ids in all comparisons.
    """
    logger.debug(f"Try to rename LLM '{old_name}' to '{new_name}' in comparisons.")

    row_count = 0
    async with get_session() as session:
        for k in ("llm_id_a", "llm_id_b"):
            logger.debug(f"Searching for comparisons with '{old_name}' in '{k}'")
            query = (
                update(Comparison)
                .where(col(getattr(Comparison, k)) == old_name)
                .values({k: new_name})
            )
            results = await session.exec(query)
            row_count += results.rowcount

        if not row_count:
            logger.info(f"No comparisons with LLM '{old_name}' to rename found!")
        elif commit:
            await session.commit()
            logger.info(
                f"Successfully renamed LLM '{old_name}' to '{new_name}' in {row_count} comparisons."
            )
        else:
            logger.warning(
                f"Would have renamed LLM '{old_name}' to '{new_name}' in {row_count} comparisons."
            )
