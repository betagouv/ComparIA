"""
Database queries for fetching vote and reaction data for ranking computation.

Uses psycopg2 with RealDictCursor, matching the existing pattern
from backend/arena/persistence.py and backend/utils/countries.py.
"""

import logging

from sqlmodel import col, select

from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.queries"))


async def fetch_votes() -> list[dict]:
    """
    Fetch all non-archived votes joined with conversations for country_portal.

    Returns:
        List of dicts with keys: model_a_name, model_b_name, chosen_model_name,
        both_equal, conv_useful_a, conv_useful_b, conv_complete_a, conv_complete_b,
        conv_creative_a, conv_creative_b, conv_clear_formatting_a, conv_clear_formatting_b,
        conv_incorrect_a, conv_incorrect_b, conv_superficial_a, conv_superficial_b,
        conv_instructions_not_followed_a, conv_instructions_not_followed_b, country_portal.
    """
    async with get_session() as session:
        results = await session.exec(
            select(
                Turn.choice,
                Turn.keyword_annotations_a,
                Turn.keyword_annotations_b,
                Comparison.llm_id_a,
                Comparison.llm_id_b,
                Comparison.country_portal,
            )
            .join(Comparison, col(Turn.comparison_id) == col(Comparison.id))
            .where(col(Comparison.archived).is_not(True))
            .where(Comparison.contains_spam == False)
            .where(
                col(Turn.choice).in_(["both_good", "both_bad", "a_better", "b_better"])
            )
        )

        return results.mappings().all()
