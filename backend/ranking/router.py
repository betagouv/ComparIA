from fastapi import APIRouter

from backend.auth.dependencies import RequiredUser

from .models import PersonalRanking
from .services import get_personal_ranking

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("/personal")
async def personal_ranking(user: RequiredUser) -> PersonalRanking:
    return await get_personal_ranking(user.id)
