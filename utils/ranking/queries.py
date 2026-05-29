"""
Database queries for fetching turns vote data for ranking computation.
"""

import logging

from sqlmodel import col, select

from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.queries"))


async def fetch_votes() -> list[dict]:
    """
    Fetch all non-archived Turn's votes joined with Comparison data.

    Returns:
        List of dicts with keys: choice, keyword_annotations_a,
        keyword_annotations_b, llm_id_a, llm_id_b.
    """
    async with get_session() as session:
        results = await session.exec(
            select(
                Turn.choice,
                Turn.keyword_annotations_a,
                Turn.keyword_annotations_b,
                Comparison.llm_id_a,
                Comparison.llm_id_b,
            )
            .join(Comparison, col(Turn.comparison_id) == col(Comparison.id))
            .where(col(Comparison.archived).is_not(True))
            .where(
                col(Turn.choice).in_(["both_good", "both_bad", "a_better", "b_better"])
            )
        )

        return results.mappings().all()
