import logging

from fastapi import APIRouter
from sqlmodel import select

from utils.database.models.llms import LLMData
from utils.database.session import get_session

logger = logging.getLogger("languia")

router = APIRouter(prefix="/llms", tags=["llms"])


@router.get("/list")
async def get_llms_list() -> list[LLMData]:
    try:
        async with get_session() as session:
            llms = (await session.exec(select(LLMData))).all()
            return llms
    except Exception as e:
        logger.error(f"[DB] Error loading LLMsData: {e}")
        raise
