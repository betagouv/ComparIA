"""
Tool specifications offered to models, and the registry of built-in tools.

The streaming loop only ever sees a `ToolSpec`: a name, a JSON schema and an
async callable. What a tool does, and whether its result counts as a success,
is the tool's own business.
"""

import asyncio
import logging
from dataclasses import replace
from typing import TYPE_CHECKING, Callable, Iterable

from sqlmodel import select

from backend.config import TOOL_REJECTION_TTL
from backend.tools.mcp_tools import resolve_mcp_tools
from backend.tools.models import ToolSpec
from backend.tools.web_search import web_search_tool_spec
from backend.utils.locale import (
    DEFAULT_LOCALES_SETTINGS,
    LocalesSettings,
    get_locales_settings,
    pick_translation,
)
from utils.database.models import Tool
from utils.database.session import get_session
from utils.i18n import SupportedLocale, TranslatableRaw
from utils.storage.redis import REDIS_TOOLS_REJECTED_KEY, get_redis_client, hash_content

if TYPE_CHECKING:
    from utils.database.models import Tool

from utils.i18n import SupportedLocale, TranslatableRaw

logger = logging.getLogger("languia")


def tool_text(
    texts: TranslatableRaw[str] | None,
    locale: SupportedLocale | None = None,
    locales: LocalesSettings = DEFAULT_LOCALES_SETTINGS,
) -> str | None:
    """A tool's name or description in the closest language it was written in."""
    if not texts:
        return None
    return pick_translation(texts, locale, locales)[1]


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


def _builtin_registry() -> dict[str, Callable[["Tool"], ToolSpec | None]]:
    return {"web_search": web_search_tool_spec}


def resolve_builtin_tools(rows: Iterable["Tool"]) -> list[ToolSpec]:
    """
    Turn built-in tool rows into specifications.

    A key that is unknown, or a tool that is not configured, yields nothing:
    the model is simply never told about it.
    """
    registry = _builtin_registry()
    specs: list[ToolSpec] = []
    for row in rows:
        build = registry.get(row.key)
        if build is None:
            logger.warning("Unknown built-in tool '%s'", row.key)
            continue
        if spec := build(row):
            specs.append(spec)
    return specs


def can_run(row: "Tool") -> bool:
    """
    Whether a row has what it needs to be offered: a built-in its
    credential, an MCP tool its address. Nothing here touches the network,
    so a server that is down still counts; the turn finds that out.
    """
    if row.kind == "mcp":
        return bool(row.url)
    return bool(resolve_builtin_tools([row]))


async def get_enabled_tools() -> list["Tool"]:
    """Tools an administrator has switched on, in display order."""
    async with get_session() as session:
        rows = await session.exec(
            select(Tool).where(Tool.enabled).order_by(Tool.created_at)
        )
        return list(rows.all())


async def get_all_tools() -> list["Tool"]:
    """All tools, in display order."""
    async with get_session() as session:
        rows = await session.exec(select(Tool).order_by(Tool.created_at))
        return list(rows.all())


async def get_offered_tools() -> list["Tool"]:
    """
    Tools a visitor may pick: switched on and able to run.

    A switched-on tool missing its credential or address is left out: picked,
    it would be quietly dropped from the turn, and the visitor would read the
    answer as the model choosing not to use it.
    """
    return [tool for tool in await get_enabled_tools() if can_run(tool)]


async def keep_offered_tools(keys: list[str]) -> list[str]:
    """
    The keys a visitor sent that name a tool on offer, each once.

    They are stored on the comparison and published with the dataset, so
    nothing else the request carries may get through.
    """
    if not keys:
        return []
    offered = {tool.key for tool in await get_offered_tools()}
    return [key for key in dict.fromkeys(keys) if key in offered]


def _first_of_each_name(specs: Iterable[ToolSpec]) -> list[ToolSpec]:
    """
    Keep one specification per name.

    Two servers may well name a function the same thing, and the loop addresses
    tools by name alone, so the second one would silently answer for the first.
    """
    kept: dict[str, ToolSpec] = {}
    for spec in specs:
        if spec.name in kept:
            logger.warning("Tool name '%s' offered twice; keeping the first", spec.name)
            continue
        kept[spec.name] = spec
    return list(kept.values())


async def resolve_tools(keys: Iterable[str]) -> list[ToolSpec]:
    """
    Turn the tool keys a visitor selected into specifications.

    This is the only place that knows one kind of tool from another. A key that
    is not enabled, or whose tool is not configured, yields nothing.
    """
    wanted = set(keys)
    if not wanted:
        return []
    selected = [tool for tool in await get_enabled_tools() if tool.key in wanted]

    # The trace keeps the name in the instance's default language: it is
    # published with the dataset, and the page shows the visitor's own.
    locales = await get_locales_settings()
    labels = {tool.key: tool_text(tool.label, None, locales) or "" for tool in selected}
    specs = resolve_builtin_tools([tool for tool in selected if tool.kind == "builtin"])
    # Servers are listed side by side: waiting on them in turn would multiply the
    # discovery timeout by the number of rows the visitor picked.
    discovered = await asyncio.gather(
        *(
            resolve_mcp_tools(tool, labels[tool.key])
            for tool in selected
            if tool.kind == "mcp"
        )
    )
    for server_specs in discovered:
        specs.extend(server_specs)
    specs = [
        replace(spec, label=labels.get(spec.tool or spec.name) or spec.label)
        for spec in specs
    ]
    return _first_of_each_name(specs)
