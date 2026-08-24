import logging

from fastapi import APIRouter
from sqlmodel import select

from utils.database.models import Tool, ToolUpsert
from utils.database.session import get_session
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/data")
async def get_data():
    async with get_session() as session:
        rows = await session.exec(select(Tool).order_by(Tool.created_at))
        return {"tools": rows.all()}


@router.get("/schemas")
async def get_schemas():
    return {"tools": ToolUpsert.model_json_schema(schema_generator=FormJsonSchema)}


@router.post("/tool")
@router.put("/tool")
async def upsert_tool(body: ToolUpsert) -> Tool:
    async with get_session() as session:
        db_tool = await session.get(Tool, body.id)
        if db_tool:
            db_tool.sqlmodel_update(body.model_dump(exclude={"id", "created_at"}))
        else:
            db_tool = Tool.model_validate(body)
        session.add(db_tool)
        await session.commit()
        await session.refresh(db_tool)
        return db_tool
