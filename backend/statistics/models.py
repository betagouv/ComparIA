from datetime import date

from pydantic import BaseModel


class DailyConversationCount(BaseModel):
    date: date
    count: int


class StatisticsSummary(BaseModel):
    questions_count: int
    votes_count: int
    daily_conversations: list[DailyConversationCount]
