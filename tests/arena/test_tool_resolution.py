"""Tests for turning configured tool rows into specifications."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.arena import tools, web_search
from utils.database.models import Tool


def _rows(*specs: tuple[str, bool]) -> list[Tool]:
    """Tool rows as the database would hand them over."""
    return [
        Tool(key=key, label=key, kind="builtin", enabled=enabled)
        for key, enabled in specs
    ]


def _with_enabled(rows: list[Tool]):
    """Stand in for the database, returning only what an admin switched on."""

    async def get_enabled_tools() -> list[Tool]:
        return [row for row in rows if row.enabled]

    return patch.object(tools, "get_enabled_tools", get_enabled_tools)


def test_enabled_row_yields_a_specification():
    asyncio.run(_test_enabled_row_yields_a_specification())


async def _test_enabled_row_yields_a_specification():
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await tools.resolve_tools(["web_search"])

    assert [spec.name for spec in specs] == ["search_web"]


def test_disabled_row_yields_nothing():
    asyncio.run(_test_disabled_row_yields_nothing())


async def _test_disabled_row_yields_nothing():
    """A tool an administrator switched off is never offered."""
    with (
        _with_enabled(_rows(("web_search", False))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await tools.resolve_tools(["web_search"])

    assert specs == []


def test_unknown_key_is_ignored_rather_than_raising():
    asyncio.run(_test_unknown_key_is_ignored_rather_than_raising())


async def _test_unknown_key_is_ignored_rather_than_raising():
    """A stale selection must not break a turn."""
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await tools.resolve_tools(["retired_tool"])

    assert specs == []


def test_selecting_nothing_never_touches_the_database():
    asyncio.run(_test_selecting_nothing_never_touches_the_database())


async def _test_selecting_nothing_never_touches_the_database():
    async def explode() -> list[Tool]:
        raise AssertionError("resolution should short-circuit on an empty selection")

    with patch.object(tools, "get_enabled_tools", explode):
        assert await tools.resolve_tools([]) == []


def test_unconfigured_tool_yields_nothing():
    asyncio.run(_test_unconfigured_tool_yields_nothing())


async def _test_unconfigured_tool_yields_nothing():
    """Enabled in the backoffice but missing its API key: still not offered."""
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", None),
    ):
        specs = await tools.resolve_tools(["web_search"])

    assert specs == []


if __name__ == "__main__":
    tests = [
        test_enabled_row_yields_a_specification,
        test_disabled_row_yields_nothing,
        test_unknown_key_is_ignored_rather_than_raising,
        test_selecting_nothing_never_touches_the_database,
        test_unconfigured_tool_yields_nothing,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tool resolution tests passed.")
