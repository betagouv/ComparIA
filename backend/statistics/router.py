from fastapi import APIRouter

from .models import StatisticsPeriod, StatisticsSummary
from .services import get_statistics_summary

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/summary", response_model=StatisticsSummary)
async def statistics_summary(period: StatisticsPeriod = "30d") -> StatisticsSummary:
    return await get_statistics_summary(period)
