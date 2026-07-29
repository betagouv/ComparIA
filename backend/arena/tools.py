"""
Tool specifications offered to models, and the registry of built-in tools.

The streaming loop only ever sees a `ToolSpec`: a name, a JSON schema and an
async callable. What a tool does, and whether its result counts as a success,
is the tool's own business.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Literal

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
