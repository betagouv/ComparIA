import logging

from fastapi import APIRouter
from sqlmodel import select

from utils.database.models.llms import LLMData, LLMEndpoint, LLMLab, LLMLicense
from utils.database.session import get_session

logger = logging.getLogger("languia")

router = APIRouter(prefix="/llms", tags=["llms"])


@router.get("/data")
async def get_data():
    try:
        async with get_session() as session:
            models = {
                "endpoints": LLMEndpoint,
                "licenses": LLMLicense,
                "labs": LLMLab,
                "llms": LLMData,
            }
            db_data = {
                k: (await session.exec(select(model).order_by(model.created_at))).all()
                for k, model in models.items()
            }

        return db_data
    except Exception as e:
        logger.error(f"[DB] Error loading LLMsData: {e}")
        raise
