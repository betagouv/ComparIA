import logging
from uuid import UUID

from sqlmodel import col, func, select

from backend.config import settings
from backend.llms.models import DatasetData
from backend.utils.countries import get_ranking
from utils.database.models import Comparison, Turn
from utils.database.models.llms import LLMData
from utils.database.session import get_session
from utils.ranking.personal import OUTCOMES, rank_personal_models, tally_votes

from .models import PersonalRanking

logger = logging.getLogger("languia")


def _general_ranks() -> dict[UUID, int]:
    """Position of each model in the last computed general ranking, if any."""
    ranking = get_ranking()
    if not ranking:
        return {}
    return {
        UUID(str(llm_id)): DatasetData.model_validate(data).rank
        for llm_id, data in ranking.rankings.items()
    }


async def get_personal_ranking(user_id: UUID) -> PersonalRanking:
    """
    Rank every model this user has voted on, from their votes alone.

    Not cached: the point of the feature is that the table moves as soon as a
    vote is cast.
    """
    empty = PersonalRanking(rows=[], votes_count=0)
    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot compute personal ranking: no database configured")
        return empty

    async with get_session() as session:
        votes = (
            await session.exec(
                select(
                    Comparison.llm_id_a,
                    Comparison.llm_id_b,
                    Turn.choice,
                    func.count(col(Turn.id)),
                )
                .join(Comparison, col(Turn.comparison_id) == col(Comparison.id))
                .where(Comparison.user_id == user_id)
                .where(col(Comparison.archived).is_not(True))
                .where(col(Turn.choice).in_(list(OUTCOMES)))
                .group_by(
                    col(Comparison.llm_id_a),
                    col(Comparison.llm_id_b),
                    col(Turn.choice),
                )
            )
        ).all()

        tallies = tally_votes(votes)
        if not tallies:
            return empty

        names = dict(
            (
                await session.exec(
                    select(LLMData.id, LLMData.name).where(
                        col(LLMData.id).in_(list(tallies))
                    )
                )
            ).all()
        )

    general_ranks = _general_ranks()
    for llm_id, tally in tallies.items():
        tally.name = names.get(llm_id, "")
        tally.general_rank = general_ranks.get(llm_id)

    return PersonalRanking(
        rows=rank_personal_models(tallies.values()),
        votes_count=sum(count for *_, count in votes),
    )
