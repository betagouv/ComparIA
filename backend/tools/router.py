import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from backend.tools.services import can_run, get_all_tools
from backend.utils.logos import logo_response
from utils.database.models import Tool, ToolPublic
from utils.database.session import get_session

logger = logging.getLogger("languia")

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def get_tools() -> list[ToolPublic]:
    """
    All tools even if disabled.
    We still need the full list to properly display logos/name in comparisons with previously enabled tools.
    """
    return [
        ToolPublic(
            **tool.model_dump(exclude={"enabled"}),
            enabled=tool.enabled and can_run(tool),
            logo_url=tool.logo_url,
        )
        for tool in await get_all_tools()
    ]


@router.get("/logo/{tool_id}", response_class=Response)
async def get_lab_logo(tool_id: UUID) -> Response:
    async with get_session() as session:
        tool = await session.get(Tool, tool_id)
        if tool is None or tool.logo is None or tool.logo_content_type is None:
            raise HTTPException(status_code=404, detail="tool_logo_not_found")

        return logo_response(
            tool.logo,
            tool.logo_content_type,
            # The URL carries the logo version, so a new upload is a new
            # URL and the old bytes can stay in the browser for a year.
            "public, max-age=31536000, immutable",
        )
