import logging
from typing import Literal
from uuid import UUID

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
    upsert_llm,
    upsert_llm_endpoint,
    upsert_llm_lab,
    upsert_llm_license,
)
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/llms", tags=["llms"])

# FIXME temp
COMMIT = False

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


@router.put("/llm/{item_id}")
async def update_llm(item_id: UUID, body: LLMDataUpsert) -> LLMData:
    body.id = item_id
    async with get_session() as session:
        return await upsert_llm(body, session, commit=COMMIT)


@router.put("/endpoint/{item_id}")
async def update_endpoint(item_id: UUID, body: LLMEndpointUpsert) -> LLMEndpoint:
    body.id = item_id
    async with get_session() as session:
        return await upsert_llm_endpoint(body, session, commit=COMMIT)


@router.put("/lab/{item_id}")
async def update_lab(item_id: UUID, body: LLMLabUpsert) -> LLMLab:
    body.id = item_id
    async with get_session() as session:
        return await upsert_llm_lab(body, session, commit=COMMIT)


@router.put("/license/{item_id}")
async def update_license(item_id: UUID, body: LLMLicenseUpsert) -> LLMLicense:
    body.id = item_id
    async with get_session() as session:
        return await upsert_llm_license(body, session, commit=COMMIT)
