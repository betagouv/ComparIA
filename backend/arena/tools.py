"""
Tool specifications offered to models, and the registry of built-in tools.

The streaming loop only ever sees a `ToolSpec`: a name, a JSON schema and an
async callable. What a tool does, and whether its result counts as a success,
is the tool's own business.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable, Literal

from backend.config import TOOL_REJECTION_TTL
from utils.storage.redis import (
    REDIS_TOOLS_REJECTED_KEY,
    get_redis_client,
    hash_content,
)

if TYPE_CHECKING:
    from utils.database.models import Tool

logger = logging.getLogger("languia")

ToolStatus = Literal["success", "empty", "error"]


@dataclass(frozen=True)
class ToolResult:
    """What a tool hands back: text for the model, plus what to record."""

    content: str
    status: ToolStatus
    results: list[Any] = field(default_factory=list)

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(
            content=json.dumps({"error": message}, ensure_ascii=False), status="error"
        )

    @classmethod
    def empty(cls, message: str) -> "ToolResult":
        return cls(
            content=json.dumps({"results": [], "message": message}, ensure_ascii=False),
            status="empty",
        )


@dataclass(frozen=True)
class ToolSpec:
    """One tool as the loop sees it."""

    name: str
    # OpenAI-style {"type": "function", "function": {...}} schema.
    schema: dict[str, Any]
    # Takes the raw JSON arguments string emitted by the model.
    run: Callable[[str], Awaitable[ToolResult]]


def _rejection_key(model: str) -> str:
    return REDIS_TOOLS_REJECTED_KEY.format(model_hash=hash_content(model))


def model_rejects_tools(model: str) -> bool:
    """
    Whether this endpoint is known to refuse tool schemas.

    Capability is learnt by trying, never declared in advance: no static
    catalogue is accurate across the providers we route to. When the answer is
    unknown -- including when Redis is unreachable -- we say no and let the
    request find out.
    """
    try:
        return bool(get_redis_client().get(_rejection_key(model)))
    except Exception as e:
        logger.warning("Could not read tool rejection cache: %s", e)
        return False


def remember_tool_rejection(model: str) -> None:
    """Record that this endpoint refused tool schemas, so we stop paying for it."""
    try:
        get_redis_client().setex(_rejection_key(model), TOOL_REJECTION_TTL, "1")
    except Exception as e:
        logger.warning("Could not store tool rejection: %s", e)


def _builtin_registry() -> dict[str, Callable[[], ToolSpec | None]]:
    # Imported here so tool modules can depend on the shapes above.
    from backend.arena.web_search import web_search_tool_spec

    return {"web_search": web_search_tool_spec}


def resolve_builtin_tools(keys: Iterable[str]) -> list[ToolSpec]:
    """
    Turn built-in tool keys into specifications.

    A key that is unknown, or a tool that is not configured, yields nothing:
    the model is simply never told about it.
    """
    registry = _builtin_registry()
    specs: list[ToolSpec] = []
    for key in keys:
        build = registry.get(key)
        if build is None:
            logger.warning("Unknown built-in tool '%s'", key)
            continue
        if spec := build():
            specs.append(spec)
    return specs


async def get_enabled_tools() -> list["Tool"]:
    """Tools an administrator has switched on, in display order."""
    from sqlmodel import select

    from utils.database.models import Tool
    from utils.database.session import get_session

    async with get_session() as session:
        rows = await session.exec(
            select(Tool).where(Tool.enabled).order_by(Tool.created_at)
        )
        return list(rows.all())


async def resolve_tools(keys: Iterable[str]) -> list[ToolSpec]:
    """
    Turn the tool keys a visitor selected into specifications.

    This is the only place that knows one kind of tool from another. A key that
    is not enabled, or whose tool is not configured, yields nothing.
    """
    wanted = set(keys)
    if not wanted:
        return []
    enabled = await get_enabled_tools()
    return resolve_builtin_tools(
        [tool.key for tool in enabled if tool.key in wanted and tool.kind == "builtin"]
    )
