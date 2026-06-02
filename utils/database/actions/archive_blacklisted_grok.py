import logging

import polars as pl
from sqlmodel import and_, col, or_, select

from ..models import Comparison
from ..session import get_session
from ..utils import archive

logger = logging.getLogger("comparia.db")


async def archive_blacklisted_grok(*, commit: bool = False) -> None:
    """
    Archive comparisons involving any Grok model (llm_id starting with 'grok-').
    """
    async with get_session() as session:
        query = select(Comparison.id, Comparison.llm_id_a, Comparison.llm_id_b).where(
            and_(
                col(Comparison.archived) == None,
                or_(
                    col(Comparison.llm_id_a).like("grok-%"),
                    col(Comparison.llm_id_b).like("grok-%"),
                ),
            )
        )
        data = pl.DataFrame((await session.exec(query)).all())

    ids = data["id"].to_list() if not data.is_empty() else []
    if not ids:
        logger.info("No comparisons with Grok models found.")
        return

    logger.warning(f"Found {len(ids)} comparisons involving Grok models.")

    grok_ids = set(
        data["llm_id_a"].append(data["llm_id_b"])
        .filter(data["llm_id_a"].append(data["llm_id_b"]).str.starts_with("grok-"))
        .unique()
        .to_list()
    )
    for grok_id in sorted(grok_ids):
        count = len(data.filter((pl.col("llm_id_a") == grok_id) | (pl.col("llm_id_b") == grok_id)))
        logger.warning(f"{count:4} comparisons with '{grok_id}'")

    await archive(ids, "blacklist_grok", commit=commit)
