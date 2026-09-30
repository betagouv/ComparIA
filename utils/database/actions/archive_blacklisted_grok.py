import logging

import polars as pl
from sqlalchemy.orm import aliased
from sqlmodel import and_, col, or_, select

from ..models import Comparison
from ..models.llms import LLMData
from ..session import get_session
from ..utils import archive

logger = logging.getLogger("comparia.db")


def blacklisted_grok_query():
    """Select comparisons using the models' stable, human-readable identifiers."""
    llm_a = aliased(LLMData)
    llm_b = aliased(LLMData)
    return (
        select(
            Comparison.id,
            llm_a.human_id.label("llm_id_a"),
            llm_b.human_id.label("llm_id_b"),
        )
        .join(llm_a, Comparison.llm_id_a == llm_a.id)
        .join(llm_b, Comparison.llm_id_b == llm_b.id)
        .where(
            and_(
                col(Comparison.archived) == None,
                or_(
                    col(llm_a.human_id).like("grok-%"),
                    col(llm_b.human_id).like("grok-%"),
                ),
            )
        )
    )


async def archive_blacklisted_grok(*, commit: bool = False) -> None:
    """
    Archive comparisons involving any Grok model (llm_id starting with 'grok-').
    """
    async with get_session() as session:
        query = blacklisted_grok_query()
        data = pl.DataFrame((await session.exec(query)).all())

    ids = data["id"].to_list() if not data.is_empty() else []
    if not ids:
        logger.info("No comparisons with Grok models found.")
        return

    logger.warning(f"Found {len(ids)} comparisons involving Grok models.")

    grok_ids = set(
        data["llm_id_a"]
        .append(data["llm_id_b"])
        .filter(data["llm_id_a"].append(data["llm_id_b"]).str.starts_with("grok-"))
        .unique()
        .to_list()
    )
    for grok_id in sorted(grok_ids):
        count = len(
            data.filter(
                (pl.col("llm_id_a") == grok_id) | (pl.col("llm_id_b") == grok_id)
            )
        )
        logger.warning(f"{count:4} comparisons with '{grok_id}'")

    await archive(ids, "blacklist_grok", commit=commit)
