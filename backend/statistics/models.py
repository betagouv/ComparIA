from datetime import date
from typing import Literal

from pydantic import BaseModel

StatisticsPeriod = Literal["7d", "30d", "90d", "all"]
StatisticsGranularity = Literal["day", "week", "month"]


class ActivityPoint(BaseModel):
    date: date
    prompts: int
    conversations: int


class PreferenceCounts(BaseModel):
    a_better: int
    b_better: int
    both_good: int
    both_bad: int


class PreferencePoint(PreferenceCounts):
    date: date


class StatisticsSummary(BaseModel):
    period: StatisticsPeriod
    granularity: StatisticsGranularity
    prompts_count: int
    conversations_count: int
    models_count: int
    preferences: PreferenceCounts
    activity: list[ActivityPoint]
    preference_activity: list[PreferencePoint]
