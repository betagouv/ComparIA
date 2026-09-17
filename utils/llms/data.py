import logging

from pydantic import BaseModel
from sqlmodel import select

from utils.database.models.llms import (
    LLMData,
    LLMDataPublic,
    LLMDataUpsert,
    LLMEndpoint,
    LLMEndpointPublic,
    LLMEndpointUpsert,
    LLMLab,
    LLMLabPublic,
    LLMLabUpsert,
    LLMLicense,
    LLMLicensePublic,
    LLMLicenseUpsert,
)
from utils.database.session import get_session

logger = logging.getLogger("comparia.llms")


class LLMsData(BaseModel):
    endpoints: list[LLMEndpointPublic]
    licenses: list[LLMLicensePublic]
    labs: list[LLMLabPublic]
    llms: list[LLMDataPublic]


class LLMImportData(BaseModel):
    endpoints: list[LLMEndpointUpsert]
    licenses: list[LLMLicenseUpsert]
    labs: list[LLMLabUpsert]
    llms: list[LLMDataUpsert]


async def get_llms_data() -> LLMsData:
    """
    Load LLMs, licenses and labs from database.
    """
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

        data = LLMsData(**db_data)
        logger.info(f"[DB] Successfully loaded LLMsData.")
        return data
    except Exception as e:
        logger.error(f"[DB] Error loading LLMsData: {e}")
        raise
