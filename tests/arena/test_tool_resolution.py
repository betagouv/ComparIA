"""Tests for turning configured tool rows into specifications."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.tools import services, web_search
from backend.utils.locale import LocalesSettings
from utils.database.models import Tool

MODULES = [services]


@pytest.fixture(autouse=True)
def _locales(monkeypatch):
    """Stand in for the app settings: French and English, French first."""

    async def locales() -> LocalesSettings:
        return LocalesSettings(default="fr", enabled=["fr", "en"])

    for module in MODULES:
        monkeypatch.setattr(module, "get_locales_settings", locales)


def _rows(*specs: tuple[str, bool]) -> list[Tool]:
    """Tool rows as the database would hand them over."""
    return [
        Tool(key=key, label={"fr": key}, kind="builtin", enabled=enabled)
        for key, enabled in specs
    ]


def _with_enabled(rows: list[Tool]):
    """Stand in for the database, returning only what an admin switched on."""

    async def get_enabled_tools() -> list[Tool]:
        return [row for row in rows if row.enabled]

    return patch.object(services, "get_enabled_tools", get_enabled_tools)


def test_enabled_row_yields_a_specification():
    asyncio.run(_test_enabled_row_yields_a_specification())


async def _test_enabled_row_yields_a_specification():
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await services.resolve_tools(["web_search"])

    assert [spec.name for spec in specs] == ["web_search"]


def test_disabled_row_yields_nothing():
    asyncio.run(_test_disabled_row_yields_nothing())


async def _test_disabled_row_yields_nothing():
    """A tool an administrator switched off is never offered."""
    with (
        _with_enabled(_rows(("web_search", False))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await services.resolve_tools(["web_search"])

    assert specs == []


def test_unknown_key_is_ignored_rather_than_raising():
    asyncio.run(_test_unknown_key_is_ignored_rather_than_raising())


async def _test_unknown_key_is_ignored_rather_than_raising():
    """A stale selection must not break a turn."""
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        specs = await services.resolve_tools(["retired_tool"])

    assert specs == []


def test_selecting_nothing_never_touches_the_database():
    asyncio.run(_test_selecting_nothing_never_touches_the_database())


async def _test_selecting_nothing_never_touches_the_database():
    async def explode() -> list[Tool]:
        raise AssertionError("resolution should short-circuit on an empty selection")

    with patch.object(services, "get_enabled_tools", explode):
        assert await services.resolve_tools([]) == []


def test_unconfigured_tool_yields_nothing():
    asyncio.run(_test_unconfigured_tool_yields_nothing())


async def _test_unconfigured_tool_yields_nothing():
    """Enabled in the backoffice but missing its API key: still not offered."""
    with (
        _with_enabled(_rows(("web_search", True))),
        patch.object(web_search.settings, "LINKUP_API_KEY", None),
    ):
        specs = await services.resolve_tools(["web_search"])

    assert specs == []


def test_public_shape_never_carries_server_credentials():
    """
    The arena serves this without authentication.

    Deriving it from the row would publish the server address and its
    credentials to every visitor the moment either is filled in.
    """
    from utils.database.models import ToolPublic

    row = Tool(
        key="datagouv",
        label={"fr": "Données publiques"},
        kind="mcp",
        url="https://mcp.data.gouv.fr/mcp",
        secret_encrypted="encrypted-secret-token",
        enabled=True,
    )
    served = ToolPublic.model_validate(
        row.model_dump() | {"label": "Données publiques"}
    ).model_dump()

    assert set(served) == {"key", "label", "description", "enabled", "logo_url"}
    assert "secret-token" not in str(served)
    assert "mcp.data.gouv.fr" not in str(served)


if __name__ == "__main__":
    tests = [
        test_enabled_row_yields_a_specification,
        test_disabled_row_yields_nothing,
        test_unknown_key_is_ignored_rather_than_raising,
        test_selecting_nothing_never_touches_the_database,
        test_unconfigured_tool_yields_nothing,
        test_public_shape_never_carries_server_credentials,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tool resolution tests passed.")
