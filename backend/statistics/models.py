from datetime import date
from typing import Literal

from pydantic import BaseModel

StatisticsPeriod = Literal["7d", "30d", "90d", "all"]
StatisticsGranularity = Literal["day", "week", "month"]


class ActivityPoint(BaseModel):
    date: date
    prompts: int
    conversations: int


class StatisticsSummary(BaseModel):
    period: StatisticsPeriod
    granularity: StatisticsGranularity
    range_start: date
    range_end: date
    prompts_count: int
    conversations_count: int
    votes_count: int
    models_count: int
    activity: list[ActivityPoint]
