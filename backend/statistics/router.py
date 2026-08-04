from fastapi import APIRouter

from .models import StatisticsSummary
from .services import get_statistics_summary

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/summary", response_model=StatisticsSummary)
async def statistics_summary() -> StatisticsSummary:
    return await get_statistics_summary()
