from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlmodel import select

from backend.llms.data import LLMList, get_llms_list
from utils.database.models.llms import LLMLab
from utils.database.session import get_session

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models() -> LLMList:
    return await get_llms_list()


@router.get("/labs/{lab_id}/logo", response_class=Response)
async def get_lab_logo(lab_id: UUID) -> Response:
    async with get_session() as session:
        result = await session.exec(select(LLMLab).where(LLMLab.id == lab_id))
        lab = result.one_or_none()
        if lab is None or lab.logo_data is None or lab.logo_content_type is None:
            raise HTTPException(status_code=404, detail="lab_logo_not_found")
        return Response(
            content=lab.logo_data,
            media_type=lab.logo_content_type,
            headers={
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "public, max-age=3600",
            },
        )
