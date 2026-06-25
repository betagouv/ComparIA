"""
Database queries for fetching turns vote data for ranking computation.
"""

import logging

from sqlalchemy.orm import aliased
from sqlmodel import col, select

from utils.database.models import Comparison, LLMMessage, Turn
from utils.database.session import get_session
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.queries"))


async def fetch_votes() -> list[dict]:
    """
    Fetch all non-archived Turn's votes joined with Comparison data.

    The two assistant answers (content + token count) are joined in as well so
    the ranking can control for answer style (length, markdown formatting); see
    ``utils.ranking.style_control``.

    Returns:
        List of dicts with keys: choice, keyword_annotations_a,
        keyword_annotations_b, llm_id_a, llm_id_b, content_a, content_b,
        tokens_a, tokens_b.
    """
    msg_a = aliased(LLMMessage)
    msg_b = aliased(LLMMessage)
    async with get_session() as session:
        results = await session.exec(
            select(
                Turn.choice,
                Turn.keyword_annotations_a,
                Turn.keyword_annotations_b,
                Comparison.llm_id_a,
                Comparison.llm_id_b,
                col(msg_a.content).label("content_a"),
                col(msg_b.content).label("content_b"),
                col(msg_a.tokens).label("tokens_a"),
                col(msg_b.tokens).label("tokens_b"),
            )
            .join(Comparison, col(Turn.comparison_id) == col(Comparison.id))
            .join(msg_a, col(Turn.llm_msg_a_id) == col(msg_a.id), isouter=True)
            .join(msg_b, col(Turn.llm_msg_b_id) == col(msg_b.id), isouter=True)
            .where(col(Comparison.archived).is_not(True))
            .where(
                col(Turn.choice).in_(["both_good", "both_bad", "a_better", "b_better"])
            )
        )

        return results.mappings().all()
