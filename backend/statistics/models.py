from datetime import date
from typing import Literal

from pydantic import BaseModel

StatisticsPeriod = Literal["7d", "30d", "90d", "all"]
StatisticsGranularity = Literal["day", "week", "month"]


class ActivityPoint(BaseModel):
    date: date
    prompts: int
    conversations: int
    # The bucket still under way, with an estimate of what it will hold once
    # full, or None when it is too early to say.
    partial: bool = False
    projected_prompts: int | None = None
    projected_conversations: int | None = None


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
