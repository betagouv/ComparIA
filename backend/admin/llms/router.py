import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlmodel import SQLModel, select

from utils.database.models.llms import (
    LLMData,
    LLMDataUpsert,
    LLMEndpoint,
    LLMEndpointPublic,
    LLMEndpointUpsert,
    LLMLab,
    LLMLabPublic,
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
from utils.storage.redis import REDIS_LLMS_DATA_CACHE_KEY, invalidate_cache
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


def _to_lab_public(lab: LLMLab) -> LLMLabPublic:
    return LLMLabPublic(
        **lab.model_dump(exclude={"logo_data", "logo_content_type"}),
        has_custom_logo=lab.has_custom_logo,
    )


_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
_LOGO_MAX_SIZE = 2 * 1024 * 1024


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
            db_data["labs"] = [_to_lab_public(lab) for lab in db_data["labs"]]

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
        db_llm = await upsert_llm_data(body, session)
        await session.refresh(db_llm)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return db_llm


@router.post("/endpoint")
@router.put("/endpoint")
async def upsert_endpoint(body: LLMEndpointUpsert) -> LLMEndpointPublic:
    async with get_session() as session:
        endpoint = await upsert_llm_endpoint(body, session)
        # Commit expires the attributes, and the instance detaches when the
        # session closes, so refresh and build the payload here.
        await session.refresh(endpoint)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return _to_endpoint_public(endpoint)


@router.delete("/endpoint/{endpoint_id}/api-key")
async def delete_endpoint_api_key(endpoint_id: UUID) -> LLMEndpointPublic:
    async with get_session() as session:
        endpoint = await clear_llm_endpoint_api_key(endpoint_id, session)
        if not endpoint:
            raise HTTPException(status_code=404, detail="endpoint_not_found")
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return _to_endpoint_public(endpoint)


@router.post("/lab")
@router.put("/lab")
async def upsert_lab(body: LLMLabUpsert):
    async with get_session() as session:
        db_lab = await upsert_llm_lab(body, session)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        await session.refresh(db_lab)
        return _to_lab_public(db_lab)


@router.put("/lab/{lab_id}/logo")
async def upload_lab_logo(lab_id: UUID, file: UploadFile):
    if file.content_type not in _LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )
    content = await file.read(_LOGO_MAX_SIZE + 1)
    if len(content) > _LOGO_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file is too large (max 2 MB)",
        )
    async with get_session() as session:
        lab = await session.get(LLMLab, lab_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="lab_not_found")
        lab.logo_data = content
        lab.logo_content_type = file.content_type
        session.add(lab)
        await session.commit()
        await session.refresh(lab)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return _to_lab_public(lab)


@router.delete("/lab/{lab_id}/logo")
async def delete_lab_logo(lab_id: UUID):
    async with get_session() as session:
        lab = await session.get(LLMLab, lab_id)
        if lab is None:
            raise HTTPException(status_code=404, detail="lab_not_found")
        lab.logo_data = None
        lab.logo_content_type = None
        session.add(lab)
        await session.commit()
        await session.refresh(lab)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return _to_lab_public(lab)


@router.post("/license")
@router.put("/license")
async def upsert_license(body: LLMLicenseUpsert) -> LLMLicense:
    async with get_session() as session:
        db_license = await upsert_llm_license(body, session)
        await session.refresh(db_license)
        invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
        return db_license
