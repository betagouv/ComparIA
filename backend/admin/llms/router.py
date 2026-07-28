import logging
from typing import Literal

from fastapi import APIRouter
from sqlmodel import SQLModel, select

from utils.database.models.llms import (
    LLMData,
    LLMDataUpsert,
    LLMEndpoint,
    LLMEndpointUpsert,
    LLMLab,
    LLMLabUpsert,
    LLMLicense,
    LLMLicenseUpsert,
)
from utils.database.session import get_session
from utils.llms.services import (
    upsert_llm_data,
    upsert_llm_endpoint,
    upsert_llm_lab,
    upsert_llm_license,
)
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/llms", tags=["llms"])


ModelKind = Literal["endpoints", "licenses", "labs", "llms"]
MODELS_UPSERT: dict[ModelKind, SQLModel] = {
    "endpoints": LLMEndpointUpsert,
    "licenses": LLMLicenseUpsert,
    "labs": LLMLabUpsert,
    "llms": LLMDataUpsert,
}


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


@router.get("/schemas")
async def get_schema():
    return {
        k: model.model_json_schema(schema_generator=FormJsonSchema)
        for k, model in MODELS_UPSERT.items()
    }


@router.post("/llm")
@router.put("/llm")
async def upsert_llm(body: LLMDataUpsert) -> LLMData:
    async with get_session() as session:
        return await upsert_llm_data(body, session)


@router.post("/endpoint")
@router.put("/endpoint")
async def upsert_endpoint(body: LLMEndpointUpsert) -> LLMEndpoint:
    async with get_session() as session:
        return await upsert_llm_endpoint(body, session)


@router.post("/lab")
@router.put("/lab")
async def upsert_lab(body: LLMLabUpsert) -> LLMLab:
    async with get_session() as session:
        return await upsert_llm_lab(body, session)


@router.post("/license")
@router.put("/license")
async def upsert_license(body: LLMLicenseUpsert) -> LLMLicense:
    async with get_session() as session:
        return await upsert_llm_license(body, session)
