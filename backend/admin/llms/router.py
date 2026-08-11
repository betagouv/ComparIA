import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import SQLModel, select

from utils.database.models.llms import (
    LLMData,
    LLMDataUpsert,
    LLMEndpoint,
    LLMEndpointPublic,
    LLMEndpointUpsert,
    LLMLab,
    LLMLabUpsert,
    LLMLicense,
    LLMLicenseUpsert,
)
from utils.database.session import get_session
from utils.llms.services import (
    clear_llm_endpoint_api_key,
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


def _to_endpoint_public(endpoint: LLMEndpoint) -> LLMEndpointPublic:
    """The endpoint without its key. Call inside the session that loaded it."""
    return LLMEndpointPublic(
        **endpoint.model_dump(exclude={"api_key"}), has_api_key=bool(endpoint.api_key)
    )


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
            # The key never leaves the backend. The panel only ever needed to
            # know whether one is set.
            db_data["endpoints"] = [
                _to_endpoint_public(endpoint) for endpoint in db_data["endpoints"]
            ]

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
async def upsert_endpoint(body: LLMEndpointUpsert) -> LLMEndpointPublic:
    async with get_session() as session:
        endpoint = await upsert_llm_endpoint(body, session)
        # Commit expires the attributes, and the instance detaches when the
        # session closes, so refresh and build the payload here.
        await session.refresh(endpoint)
        return _to_endpoint_public(endpoint)


@router.delete("/endpoint/{endpoint_id}/api-key")
async def delete_endpoint_api_key(endpoint_id: UUID) -> LLMEndpointPublic:
    async with get_session() as session:
        endpoint = await clear_llm_endpoint_api_key(endpoint_id, session)
        if not endpoint:
            raise HTTPException(status_code=404, detail="endpoint_not_found")
        return _to_endpoint_public(endpoint)


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
