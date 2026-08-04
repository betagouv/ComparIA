from pydantic import BaseModel


class StatisticsSummary(BaseModel):
    questions_count: int
    votes_count: int
