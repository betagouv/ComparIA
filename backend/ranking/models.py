from pydantic import BaseModel

from utils.ranking.personal import PersonalRankingRow


class PersonalRanking(BaseModel):
    """
    The signed-in user's own ranking, already scored, ordered and numbered.

    Rows carry no model metadata beyond the identity: the client joins them on
    the model list it already holds.
    """

    rows: list[PersonalRankingRow]
    votes_count: int
