"""Tests for offering an MCP server's functions as ordinary tools."""

import asyncio
import json
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.arena import mcp_tools, tools
from backend.config import MCP_SCHEMA_TTL
from utils.database.models import Tool

DATAGOUV = Tool(
    key="datagouv",
    label="Données publiques",
    kind="mcp",
    url="https://mcp.data.gouv.fr/mcp",
    enabled=True,
)

SERVER_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_datasets",
            "description": "Search public datasets.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dataset",
            "description": "Fetch one dataset.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class FakeRedis:
    """Just enough Redis to exercise the freshness and staleness paths."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value

    def age(self, seconds: float) -> None:
        for key, raw in self.values.items():
            entry = json.loads(raw)
            entry["fetched_at"] -= seconds
            self.values[key] = json.dumps(entry)


def _with_redis(client: FakeRedis):
    return patch.object(mcp_tools, "get_redis_client", lambda: client)


def _listing(schemas: list[Any] | None):
    """Stand in for the MCP client: hand back schemas, or refuse to answer."""

    async def list_server(row: Tool) -> list[Any]:
        if schemas is None:
            raise ConnectionError("server unreachable")
        return schemas

    return patch.object(mcp_tools, "_list_server", list_server)


def _with_enabled(rows: list[Tool]):
    async def get_enabled_tools() -> list[Tool]:
        return [row for row in rows if row.enabled]

    return patch.object(tools, "get_enabled_tools", get_enabled_tools)


def test_mcp_row_yields_specifications_like_any_other():
    asyncio.run(_test_mcp_row_yields_specifications_like_any_other())


async def _test_mcp_row_yields_specifications_like_any_other():
    """One row, several functions, and nothing the loop can tell apart."""
    with _with_redis(FakeRedis()), _listing(SERVER_SCHEMAS), _with_enabled([DATAGOUV]):
        specs = await tools.resolve_tools(["datagouv"])

    assert [spec.name for spec in specs] == ["search_datasets", "get_dataset"]
    assert all(isinstance(spec, tools.ToolSpec) for spec in specs)
    assert [spec.schema for spec in specs] == SERVER_SCHEMAS
    assert all(asyncio.iscoroutinefunction(spec.run) for spec in specs)


def test_both_kinds_resolve_to_one_uniform_list():
    asyncio.run(_test_both_kinds_resolve_to_one_uniform_list())


async def _test_both_kinds_resolve_to_one_uniform_list():
    """The loop is handed one list and cannot tell where an entry came from."""
    from backend.arena import web_search

    rows = [
        Tool(key="web_search", label="Recherche web", kind="builtin", enabled=True),
        DATAGOUV,
    ]
    with (
        _with_redis(FakeRedis()),
        _listing(SERVER_SCHEMAS),
        _with_enabled(rows),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await tools.resolve_tools(["web_search", "datagouv"])

    assert [spec.name for spec in specs] == [
        "web_search",
        "search_datasets",
        "get_dataset",
    ]
    assert all(spec.schema["type"] == "function" for spec in specs)


def test_schemas_are_served_stale_when_a_refresh_fails():
    asyncio.run(_test_schemas_are_served_stale_when_a_refresh_fails())


async def _test_schemas_are_served_stale_when_a_refresh_fails():
    """A server that answered once keeps its tools on offer while it is down."""
    redis = FakeRedis()
    with _with_redis(redis), _listing(SERVER_SCHEMAS):
        await mcp_tools.discover_schemas(DATAGOUV)

    redis.age(MCP_SCHEMA_TTL + 1)
    with _with_redis(redis), _listing(None):
        schemas = await mcp_tools.discover_schemas(DATAGOUV)

    assert schemas == SERVER_SCHEMAS


def test_fresh_schemas_are_not_asked_for_again():
    asyncio.run(_test_fresh_schemas_are_not_asked_for_again())


async def _test_fresh_schemas_are_not_asked_for_again():
    redis = FakeRedis()
    with _with_redis(redis), _listing(SERVER_SCHEMAS):
        await mcp_tools.discover_schemas(DATAGOUV)

    async def explode(row: Tool) -> list[dict]:
        raise AssertionError("a fresh cache entry should be enough")

    with _with_redis(redis), patch.object(mcp_tools, "_list_server", explode):
        assert await mcp_tools.discover_schemas(DATAGOUV) == SERVER_SCHEMAS


def test_unreachable_server_yields_nothing_and_raises_nothing():
    asyncio.run(_test_unreachable_server_yields_nothing_and_raises_nothing())


async def _test_unreachable_server_yields_nothing_and_raises_nothing():
    """No cache, no server: the model is simply never told the tool exists."""
    with _with_redis(FakeRedis()), _listing(None), _with_enabled([DATAGOUV]):
        specs = await tools.resolve_tools(["datagouv"])

    assert specs == []


def test_a_server_that_never_answers_is_dropped_within_the_timeout():
    asyncio.run(_test_a_server_that_never_answers_is_dropped_within_the_timeout())


async def _test_a_server_that_never_answers_is_dropped_within_the_timeout():
    """A hanging server must not hold the turn open."""

    @asynccontextmanager
    async def hang(url: str, auth_header: str | None):
        await asyncio.sleep(30)
        yield None

    with (
        _with_redis(FakeRedis()),
        patch.object(mcp_tools, "_session", hang),
        patch.object(mcp_tools, "MCP_DISCOVERY_TIMEOUT_SECONDS", 0.05),
    ):
        started = time.monotonic()
        specs = await mcp_tools.resolve_mcp_tools(DATAGOUV)

    assert specs == []
    assert time.monotonic() - started < 5


def test_nonsense_from_a_server_yields_nothing():
    asyncio.run(_test_nonsense_from_a_server_yields_nothing())


async def _test_nonsense_from_a_server_yields_nothing():
    """Whatever comes back, the turn survives it."""
    with _with_redis(FakeRedis()), _listing(["not a schema"]):
        assert await mcp_tools.resolve_mcp_tools(DATAGOUV) == []


def test_a_row_without_an_address_yields_nothing():
    asyncio.run(_test_a_row_without_an_address_yields_nothing())


async def _test_a_row_without_an_address_yields_nothing():
    row = Tool(key="broken", label="Cassé", kind="mcp", enabled=True)
    assert await mcp_tools.resolve_mcp_tools(row) == []


def test_authentication_header_is_read_and_malformed_ones_ignored():
    assert mcp_tools._headers("Authorization: Bearer abc") == {
        "Authorization": "Bearer abc"
    }
    assert mcp_tools._headers(None) is None
    assert mcp_tools._headers("nonsense") is None


def test_a_successful_call_records_what_came_back():
    asyncio.run(_test_a_successful_call_records_what_came_back())


async def _test_a_successful_call_records_what_came_back():
    """
    The trace holds the result, not just the answer.

    Left empty, the interface tells the visitor a successful call returned
    nothing.
    """

    class Block:
        text = "Trois jeux de données correspondent."

    class Reply:
        isError = False
        content = [Block()]

    async def call_openai_tool(session, openai_tool):
        return Reply()

    with (
        _with_redis(FakeRedis()),
        _listing(SERVER_SCHEMAS),
        _with_enabled([DATAGOUV]),
        patch.object(mcp_tools, "_session", _fake_session()),
        patch(
            "litellm.experimental_mcp_client.call_openai_tool",
            call_openai_tool,
        ),
    ):
        specs = await tools.resolve_tools([DATAGOUV.key])
        result = await specs[0].run("{}")

    assert result.status == "success"
    assert [(source.name, source.content) for source in result.results] == [
        (DATAGOUV.label, "Trois jeux de données correspondent.")
    ]
    assert result.results[0].url is None


def _fake_session():
    """An MCP session that connects to nothing."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def session(url, auth_header):
        yield object()

    return session


if __name__ == "__main__":
    tests = [
        test_mcp_row_yields_specifications_like_any_other,
        test_both_kinds_resolve_to_one_uniform_list,
        test_schemas_are_served_stale_when_a_refresh_fails,
        test_fresh_schemas_are_not_asked_for_again,
        test_unreachable_server_yields_nothing_and_raises_nothing,
        test_a_server_that_never_answers_is_dropped_within_the_timeout,
        test_nonsense_from_a_server_yields_nothing,
        test_a_row_without_an_address_yields_nothing,
        test_authentication_header_is_read_and_malformed_ones_ignored,
        test_a_successful_call_records_what_came_back,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} MCP tool tests passed.")
