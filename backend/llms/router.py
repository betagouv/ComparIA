from fastapi import APIRouter

from backend.llms.data import LLMList, get_llms_list

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models() -> LLMList:
    return await get_llms_list()
