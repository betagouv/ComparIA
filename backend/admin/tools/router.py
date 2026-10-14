import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.admin.tools.models import (
    ToolDraft,
    ToolHealth,
    ToolSwitch,
    ToolTestResult,
    ToolUsage,
)
from backend.admin.tools.services import (
    check_draft,
    check_tool,
    clear_tool_secret,
    set_tool_enabled,
    to_admin,
    tool_usage,
    tools_health,
    upsert_tool,
)
from utils.database.models import Tool, ToolAdmin, ToolUpsert
from utils.database.session import get_session
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/data")
async def get_data() -> dict[str, list[ToolAdmin]]:
    async with get_session() as session:
        rows = await session.exec(select(Tool).order_by(Tool.created_at))
        # The credential never leaves the backend. The panel only needs to
        # know whether one is set.
        return {"tools": [to_admin(row) for row in rows.all()]}


@router.get("/usage")
async def get_usage() -> list[ToolUsage]:
    async with get_session() as session:
        rows = (await session.exec(select(Tool))).all()
        return await tool_usage(list(rows), session)


@router.get("/health")
async def get_health(refresh: bool = False) -> list[ToolHealth]:
    # Slow on a cold cache: one call per server. The list asks for it after
    # it has shown the tools, not before.
    async with get_session() as session:
        rows = (await session.exec(select(Tool))).all()
    return await tools_health(list(rows), refresh)


@router.get("/schemas")
async def get_schemas():
    return {"tools": ToolUpsert.model_json_schema(schema_generator=FormJsonSchema)}


@router.post("/tool")
@router.put("/tool")
async def upsert(body: ToolUpsert) -> ToolAdmin:
    async with get_session() as session:
        return to_admin(await upsert_tool(body, session))


@router.patch("/tool/{tool_id}")
async def switch(tool_id: UUID, body: ToolSwitch) -> ToolAdmin:
    # Only the switch: the list page has no credential or allowlist to send
    # back, and a full upsert from it would have to.
    async with get_session() as session:
        row = await set_tool_enabled(tool_id, body.enabled, session)
        if not row:
            raise HTTPException(status_code=404, detail="tool_not_found")
        return to_admin(row)


@router.delete("/tool/{tool_id}/secret")
async def delete_secret(tool_id: UUID) -> ToolAdmin:
    async with get_session() as session:
        row = await clear_tool_secret(tool_id, session)
        if not row:
            raise HTTPException(status_code=404, detail="tool_not_found")
        return to_admin(row)


@router.post("/tool/{tool_id}/test")
async def check(tool_id: UUID) -> ToolTestResult:
    async with get_session() as session:
        row = await session.get(Tool, tool_id)
        if not row:
            raise HTTPException(status_code=404, detail="tool_not_found")
    return await check_tool(row)


@router.post("/test")
async def check_unsaved(body: ToolDraft) -> ToolTestResult:
    return await check_draft(body)
