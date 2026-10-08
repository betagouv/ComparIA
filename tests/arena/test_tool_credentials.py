"""Tests for credentials and filters an administrator sets on a tool row."""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.arena import mcp_tools, tools, web_search
from utils.database.models import Tool, ToolUpsert
from utils.secrets import encrypt_secret

from tests.arena.test_mcp_tools import SERVER_SCHEMAS, FakeRedis, _listing, _with_redis


def _web_search_row(**fields) -> Tool:
    return Tool(
        key="web_search", label="Recherche web", kind="builtin", enabled=True, **fields
    )


def test_the_row_key_wins_over_the_environment():
    row = _web_search_row(secret_encrypted=encrypt_secret("key-from-admin"))
    with patch.object(web_search.settings, "LINKUP_API_KEY", "key-from-env"):
        config = web_search.web_search_config(row)

    assert config is not None
    assert config.api_key == "key-from-admin"


def test_the_environment_key_still_serves_a_row_without_one():
    """Instances configured before the back office held the key keep working."""
    with patch.object(web_search.settings, "LINKUP_API_KEY", "key-from-env"):
        config = web_search.web_search_config(_web_search_row())

    assert config is not None
    assert config.api_key == "key-from-env"


def test_no_key_anywhere_means_web_search_is_not_offered():
    row = _web_search_row()
    with patch.object(web_search.settings, "LINKUP_API_KEY", None):
        assert tools.resolve_builtin_tools([row]) == []
        assert tools.can_run(row) is False


def test_a_credential_no_key_opens_is_treated_as_missing():
    """A rotated-away key must take the tool off offer, not fail every call."""
    row = _web_search_row(secret_encrypted="not-a-fernet-token")
    with patch.object(web_search.settings, "LINKUP_API_KEY", None):
        assert tools.read_secret(row) is None
        assert tools.can_run(row) is False


def test_domain_filters_reach_linkup_and_the_model():
    asyncio.run(_test_domain_filters_reach_linkup_and_the_model())


async def _test_domain_filters_reach_linkup_and_the_model():
    row = _web_search_row(
        secret_encrypted=encrypt_secret("key"),
        allowed_domains=["service-public.fr", "legifrance.gouv.fr"],
    )
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, api_key: str) -> None:
            calls.append({"api_key": api_key})

        async def async_search(self, **kwargs):
            calls[-1].update(kwargs)
            return SimpleNamespace(results=[])

    with (
        patch.object(web_search, "LinkupClient", FakeClient),
        patch.object(web_search.settings, "CACHE_ENABLED", False),
    ):
        [spec] = tools.resolve_builtin_tools([row])
        await spec.run(json.dumps({"query": "droit au chômage"}))

    assert calls[0]["api_key"] == "key"
    assert calls[0]["include_domains"] == ["service-public.fr", "legifrance.gouv.fr"]
    assert calls[0]["exclude_domains"] is None
    assert "service-public.fr" in spec.schema["function"]["description"]
    # The shared schema is left alone for every other row.
    assert "service-public.fr" not in json.dumps(web_search.WEB_SEARCH_TOOL_SCHEMA)


def test_the_same_query_under_other_filters_is_another_cache_entry():
    unfiltered = web_search.WebSearchConfig(api_key="key")
    filtered = web_search.WebSearchConfig(api_key="key", exclude_domains=["x.com"])

    assert unfiltered.cache_scope == ""
    assert filtered.cache_scope != unfiltered.cache_scope


def test_an_allowlist_offers_only_the_functions_it_names():
    asyncio.run(_test_an_allowlist_offers_only_the_functions_it_names())


async def _test_an_allowlist_offers_only_the_functions_it_names():
    row = Tool(
        key="datagouv",
        label="Données publiques",
        kind="mcp",
        url="https://mcp.data.gouv.fr/mcp",
        allowed_functions=["get_dataset"],
        enabled=True,
    )
    with _with_redis(FakeRedis()), _listing(SERVER_SCHEMAS):
        specs = await mcp_tools.resolve_mcp_tools(row)

    assert [spec.name for spec in specs] == ["get_dataset"]


def test_no_allowlist_offers_every_function():
    asyncio.run(_test_no_allowlist_offers_every_function())


async def _test_no_allowlist_offers_every_function():
    row = Tool(key="datagouv", label="Données", kind="mcp", url="https://x.fr/mcp")
    with _with_redis(FakeRedis()), _listing(SERVER_SCHEMAS):
        specs = await mcp_tools.resolve_mcp_tools(row)

    assert [spec.name for spec in specs] == ["search_datasets", "get_dataset"]


def test_the_server_is_sent_the_decrypted_credential():
    row = Tool(
        key="private",
        label="Privé",
        kind="mcp",
        url="https://x.fr/mcp",
        secret_encrypted=encrypt_secret("X-API-Key: s3cret"),
    )

    assert mcp_tools._headers(tools.read_secret(row)) == {"X-API-Key": "s3cret"}


def test_an_mcp_row_without_an_address_cannot_run():
    assert tools.can_run(Tool(key="m", label="M", kind="mcp")) is False
    assert tools.can_run(Tool(key="m", label="M", kind="mcp", url="https://x.fr")) is True


def test_domains_are_normalised_from_what_an_admin_pastes():
    body = ToolUpsert(
        key="web_search",
        label="Recherche web",
        allowed_domains=["https://www.Service-Public.fr/particuliers", " ", "service-public.fr"],
    )

    assert body.allowed_domains == ["service-public.fr"]


def test_allowed_and_blocked_domains_cannot_both_be_set():
    with pytest.raises(ValidationError, match="not both"):
        ToolUpsert(
            key="web_search",
            label="Recherche web",
            allowed_domains=["a.fr"],
            blocked_domains=["b.fr"],
        )


def test_a_domain_that_is_not_one_is_refused():
    with pytest.raises(ValidationError, match="not a domain"):
        ToolUpsert(key="web_search", label="Recherche web", blocked_domains=["localhost"])


def test_blank_function_names_are_dropped():
    body = ToolUpsert(key="m", label="M", kind="mcp", allowed_functions=[" ", "a "])

    assert body.allowed_functions == ["a"]
    assert ToolUpsert(key="m", label="M", allowed_functions=[""]).allowed_functions is None
