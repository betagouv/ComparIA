import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from linkup import (
    LinkupAuthenticationError,
    LinkupClient,
    LinkupInsufficientCreditError,
    LinkupNoResultError,
)
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.admin.tools.models import (
    ToolDraft,
    ToolFunction,
    ToolHealth,
    ToolTestError,
    ToolTestResult,
    ToolUsage,
)
from backend.arena.mcp_tools import list_server_functions
from backend.arena.web_search import WEB_SEARCH_TOOL_NAME, web_search_config
from backend.config import (
    TOOL_HEALTH_TTL,
    TOOL_USAGE_DAYS,
    WEB_SEARCH_TOOL_TIMEOUT_SECONDS,
)
from utils.database.models import Tool, ToolAdmin, ToolUpsert
from utils.secrets import encrypt_secret
from utils.storage.redis import REDIS_TOOL_HEALTH_KEY, get_redis_client, hash_content

logger = logging.getLogger("languia")


def to_admin(row: Tool) -> ToolAdmin:
    """The row without its credential. Call inside the session that loaded it."""
    return ToolAdmin(
        **row.model_dump(exclude={"secret_encrypted"}),
        has_secret=bool(row.secret_encrypted),
    )


async def upsert_tool(body: ToolUpsert, session: AsyncSession) -> Tool:
    row = await session.get(Tool, body.id)
    if row:
        row.sqlmodel_update(body.model_dump(exclude={"id", "created_at", "secret"}))
    else:
        row = Tool.model_validate(body.model_dump(exclude={"secret"}))
    # An empty field keeps the stored credential: the panel never has it to
    # send back.
    if body.secret and body.secret.strip():
        row.secret_encrypted = encrypt_secret(body.secret.strip())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def clear_tool_secret(tool_id: UUID, session: AsyncSession) -> Tool | None:
    row = await session.get(Tool, tool_id)
    if not row:
        return None
    row.secret_encrypted = None
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


def _status_code(error: BaseException) -> int | None:
    """The HTTP status behind an MCP failure, which the client nests in
    exception groups."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code
    if isinstance(error, BaseExceptionGroup):
        for inner in error.exceptions:
            if (code := _status_code(inner)) is not None:
                return code
    if error.__cause__ is not None:
        return _status_code(error.__cause__)
    return None


def _contains(error: BaseException, kind: type[BaseException]) -> bool:
    if isinstance(error, kind):
        return True
    if isinstance(error, BaseExceptionGroup):
        return any(_contains(inner, kind) for inner in error.exceptions)
    return False


async def _test_mcp(row: Tool, remember: bool) -> ToolTestResult:
    if not row.url:
        return ToolTestResult(ok=False, error="no_url")
    try:
        functions = await list_server_functions(row, remember=remember)
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
            raise
        error: ToolTestError
        if _status_code(e) in (401, 403):
            error = "invalid_credential"
        elif _contains(e, TimeoutError):
            error = "timeout"
        else:
            error = "unreachable"
        # The type only: a message may quote the URL with its token in it.
        logger.warning("MCP test of '%s' failed: %s", row.key, type(e).__name__)
        return ToolTestResult(ok=False, error=error)
    return ToolTestResult(
        ok=True, functions=[ToolFunction(**function) for function in functions]
    )


async def _test_web_search(row: Tool) -> ToolTestResult:
    config = web_search_config(row)
    if not config:
        return ToolTestResult(ok=False, error="no_credential")
    try:
        async with asyncio.timeout(WEB_SEARCH_TOOL_TIMEOUT_SECONDS):
            await LinkupClient(api_key=config.api_key).async_search(
                query="compar:IA",
                depth="standard",
                output_type="searchResults",
                include_domains=config.include_domains,
                exclude_domains=config.exclude_domains,
                max_results=1,
            )
    except LinkupNoResultError:
        # The key was accepted; the filters simply matched nothing.
        return ToolTestResult(ok=True)
    except LinkupAuthenticationError:
        return ToolTestResult(ok=False, error="invalid_credential")
    except LinkupInsufficientCreditError:
        return ToolTestResult(ok=False, error="no_credit")
    except TimeoutError:
        return ToolTestResult(ok=False, error="timeout")
    except Exception as e:
        logger.warning("Web search test failed: %s", type(e).__name__)
        return ToolTestResult(ok=False, error="unreachable")
    return ToolTestResult(ok=True)


async def check_tool(row: Tool, remember: bool = True) -> ToolTestResult:
    """Try the tool the way a turn would, with what is stored now."""
    if row.kind == "mcp":
        return await _test_mcp(row, remember)
    if row.key == WEB_SEARCH_TOOL_NAME:
        return await _test_web_search(row)
    return ToolTestResult(ok=False, error="unknown_builtin")


async def check_draft(draft: ToolDraft) -> ToolTestResult:
    """Try a tool that is still being set up, without saving anything."""
    secret = draft.secret.strip() if draft.secret else ""
    row = Tool(
        key=draft.key or (WEB_SEARCH_TOOL_NAME if draft.kind == "builtin" else "draft"),
        label=draft.key or "draft",
        kind=draft.kind,
        url=draft.url.strip() if draft.url else None,
        secret_encrypted=encrypt_secret(secret) if secret else None,
    )
    return await check_tool(row, remember=False)


async def set_tool_enabled(
    tool_id: UUID, enabled: bool, session: AsyncSession
) -> Tool | None:
    row = await session.get(Tool, tool_id)
    if not row:
        return None
    row.enabled = enabled
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


# Every tool call in the window with the status of its result. A call is
# matched to its row by key; calls recorded before the key existed fall back
# on the label, and web search's on its function name, which is its key.
_USAGE = text("""
    WITH events AS (
        SELECT m.id AS message_id, e
        FROM llm_message m, jsonb_array_elements(m.agent_trace) e
        WHERE jsonb_typeof(m.agent_trace) = 'array' AND m.created_at >= :since
    ),
    calls AS (
        SELECT message_id, e->>'tool_call_id' AS call_id, e->>'tool' AS tool,
               e->>'label' AS label, e->>'name' AS name
        FROM events WHERE e->>'type' = 'tool_call'
    ),
    results AS (
        SELECT message_id, e->>'tool_call_id' AS call_id, e->>'status' AS status
        FROM events WHERE e->>'type' = 'tool_result'
    )
    SELECT c.tool, c.label, c.name, count(*) AS calls,
           count(*) FILTER (WHERE r.status = 'error') AS failures
    FROM calls c LEFT JOIN results r USING (message_id, call_id)
    GROUP BY c.tool, c.label, c.name
""")


async def tool_usage(rows: list[Tool], session: AsyncSession) -> list[ToolUsage]:
    since = datetime.now() - timedelta(days=TOOL_USAGE_DAYS)
    by_key = {row.key: ToolUsage(id=row.id) for row in rows}
    by_label = {row.label: by_key[row.key] for row in rows}
    for tool, label, name, calls, failures in await session.execute(
        _USAGE, {"since": since}
    ):
        usage = by_key.get(tool) or by_label.get(label) or by_key.get(name)
        if usage:
            usage.calls += calls
            usage.failures += failures
    return list(by_key.values())


def _health_key(row: Tool) -> str:
    # Anything a check depends on is in the key, so saving a new address,
    # credential or filter checks again rather than showing the old verdict.
    settings = (
        f"{row.id}|{row.url}|{row.secret_encrypted}"
        f"|{row.allowed_domains}|{row.blocked_domains}"
    )
    return REDIS_TOOL_HEALTH_KEY.format(tool_id=hash_content(settings))


async def _health(row: Tool, refresh: bool) -> ToolHealth:
    key = _health_key(row)
    if not refresh:
        try:
            if cached := get_redis_client().get(key):
                return ToolHealth.model_validate_json(cached)
        except Exception as e:
            logger.warning("Could not read tool health: %s", e)
    result = await check_tool(row)
    health = ToolHealth(
        id=row.id, ok=result.ok, error=result.error, checked_at=datetime.now(UTC)
    )
    try:
        get_redis_client().setex(key, TOOL_HEALTH_TTL, health.model_dump_json())
    except Exception as e:
        logger.warning("Could not store tool health: %s", e)
    return health


async def tools_health(rows: list[Tool], refresh: bool = False) -> list[ToolHealth]:
    """Whether each tool answers now, checked side by side."""
    return list(await asyncio.gather(*(_health(row, refresh) for row in rows)))
