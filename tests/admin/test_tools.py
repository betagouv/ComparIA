"""
The tools panel writes credentials it can never read back, and tests a tool
with what is stored.
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from linkup import LinkupAuthenticationError, LinkupNoResultError  # noqa: E402

from backend.admin.tools import admin_tools_router  # noqa: E402
from backend.admin.tools import services  # noqa: E402
from backend.arena import web_search  # noqa: E402
from utils.database.models import Tool  # noqa: E402
from utils.database.session import get_session  # noqa: E402
from utils.secrets import decrypt_secret  # noqa: E402

WEB_SEARCH = {"key": "web_search", "label": "Recherche web", "kind": "builtin"}
MCP = {
    "key": "datagouv",
    "label": "Données publiques",
    "kind": "mcp",
    "url": "https://mcp.example.org/mcp",
}


def client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(admin_tools_router)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin"
    )


async def stored(tool_id: str) -> Tool:
    async with get_session() as session:
        row = await session.get(Tool, uuid.UUID(tool_id))
        assert row is not None
        return row


async def save(api, body: dict) -> dict:
    response = await api.post("/tools/tool", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_credential_is_stored_encrypted_and_never_sent_back(database):
    async def scenario():
        async with client() as api:
            saved = await save(api, WEB_SEARCH | {"secret": "linkup-key-123"})
            listed = (await api.get("/tools/data")).json()["tools"]

        assert saved["has_secret"] is True
        assert "secret" not in saved and "secret_encrypted" not in saved
        assert "linkup-key-123" not in str(listed)
        assert listed[0]["has_secret"] is True

        row = await stored(saved["id"])
        assert row.secret_encrypted != "linkup-key-123"
        assert decrypt_secret(row.secret_encrypted) == "linkup-key-123"

    database(scenario)


def test_saving_with_the_field_empty_keeps_the_credential(database):
    async def scenario():
        async with client() as api:
            saved = await save(api, WEB_SEARCH | {"secret": "linkup-key-123"})
            again = await save(
                api, WEB_SEARCH | {"id": saved["id"], "label": "Web", "secret": ""}
            )

        assert again["label"] == "Web"
        assert again["has_secret"] is True
        row = await stored(saved["id"])
        assert decrypt_secret(row.secret_encrypted) == "linkup-key-123"

    database(scenario)


def test_removing_the_credential_has_its_own_route(database):
    async def scenario():
        async with client() as api:
            saved = await save(api, WEB_SEARCH | {"secret": "linkup-key-123"})
            removed = await api.delete(f"/tools/tool/{saved['id']}/secret")
            missing = await api.delete(f"/tools/tool/{uuid.uuid4()}/secret")

        assert removed.json()["has_secret"] is False
        assert (await stored(saved["id"])).secret_encrypted is None
        assert missing.status_code == 404

    database(scenario)


def test_conflicting_domain_lists_are_refused(database):
    async def scenario():
        async with client() as api:
            response = await api.post(
                "/tools/tool",
                json=WEB_SEARCH
                | {"allowed_domains": ["a.fr"], "blocked_domains": ["b.fr"]},
            )
        assert response.status_code == 422

    database(scenario)


def test_testing_an_mcp_server_lists_its_functions(database, monkeypatch):
    async def list_server_functions(row, remember=True):
        return [{"name": "search_datasets", "description": "Search."}]

    monkeypatch.setattr(services, "list_server_functions", list_server_functions)

    async def scenario():
        async with client() as api:
            saved = await save(api, MCP)
            result = (await api.post(f"/tools/tool/{saved['id']}/test")).json()

        assert result == {
            "ok": True,
            "error": None,
            "functions": [{"name": "search_datasets", "description": "Search."}],
        }

    database(scenario)


def test_a_server_refusing_the_credential_says_so(database, monkeypatch):
    async def list_server_functions(row, remember=True):
        request = httpx.Request("POST", row.url)
        refused = httpx.HTTPStatusError(
            "401", request=request, response=httpx.Response(401, request=request)
        )
        # How the MCP client hands it over: inside its task group's error.
        raise ExceptionGroup("task group", [refused])

    monkeypatch.setattr(services, "list_server_functions", list_server_functions)

    async def scenario():
        async with client() as api:
            saved = await save(api, MCP | {"secret": "wrong-token"})
            result = (await api.post(f"/tools/tool/{saved['id']}/test")).json()

        assert result["ok"] is False
        assert result["error"] == "invalid_credential"
        assert "wrong-token" not in str(result)

    database(scenario)


def test_an_unreachable_server_and_a_missing_address_are_told_apart(
    database, monkeypatch
):
    async def list_server_functions(row, remember=True):
        raise ConnectionError("no route to host")

    monkeypatch.setattr(services, "list_server_functions", list_server_functions)

    async def scenario():
        async with client() as api:
            down = await save(api, MCP)
            no_url = await save(api, MCP | {"key": "other", "url": None})
            down_result = (await api.post(f"/tools/tool/{down['id']}/test")).json()
            no_url_result = (await api.post(f"/tools/tool/{no_url['id']}/test")).json()

        assert down_result["error"] == "unreachable"
        assert no_url_result["error"] == "no_url"

    database(scenario)


def test_web_search_without_any_key_says_so(database, monkeypatch):
    monkeypatch.setattr(web_search.settings, "LINKUP_API_KEY", None)

    async def scenario():
        async with client() as api:
            saved = await save(api, WEB_SEARCH)
            result = (await api.post(f"/tools/tool/{saved['id']}/test")).json()

        assert result["error"] == "no_credential"

    database(scenario)


def test_web_search_test_tells_a_bad_key_from_a_good_one(database, monkeypatch):
    seen_keys: list[str] = []

    class FakeLinkup:
        def __init__(self, api_key: str) -> None:
            seen_keys.append(api_key)
            self.api_key = api_key

        async def async_search(self, **kwargs):
            if self.api_key == "bad":
                raise LinkupAuthenticationError("bad key")
            raise LinkupNoResultError("nothing")

    monkeypatch.setattr(services, "LinkupClient", FakeLinkup)

    async def scenario():
        async with client() as api:
            bad = await save(api, WEB_SEARCH | {"secret": "bad"})
            bad_result = (await api.post(f"/tools/tool/{bad['id']}/test")).json()
            await save(api, WEB_SEARCH | {"id": bad["id"], "secret": "good"})
            good_result = (await api.post(f"/tools/tool/{bad['id']}/test")).json()

        assert bad_result["error"] == "invalid_credential"
        # No result for the probe query still means the key was accepted.
        assert good_result["ok"] is True
        assert seen_keys == ["bad", "good"]

    database(scenario)


def test_the_list_switches_a_tool_on_and_off_and_nothing_else(database):
    async def scenario():
        async with client() as api:
            saved = await save(
                api,
                MCP | {"secret": "token", "allowed_functions": ["search_datasets"]},
            )
            on = await api.patch(f"/tools/tool/{saved['id']}", json={"enabled": True})
            missing = await api.patch(
                f"/tools/tool/{uuid.uuid4()}", json={"enabled": True}
            )

        assert on.json()["enabled"] is True
        assert missing.status_code == 404
        row = await stored(saved["id"])
        assert row.enabled is True
        assert decrypt_secret(row.secret_encrypted) == "token"
        assert row.allowed_functions == ["search_datasets"]

    database(scenario)


def test_a_tool_is_tested_before_it_is_saved(database, monkeypatch):
    seen = {}

    async def list_server_functions(row, remember=True):
        seen.update(url=row.url, secret=decrypt_secret(row.secret_encrypted))
        seen["remember"] = remember
        return [{"name": "search_datasets", "description": "Search."}]

    monkeypatch.setattr(services, "list_server_functions", list_server_functions)

    async def scenario():
        async with client() as api:
            response = await api.post(
                "/tools/test",
                json={"kind": "mcp", "url": MCP["url"], "secret": " token "},
            )
            listed = (await api.get("/tools/data")).json()["tools"]

        assert response.json()["functions"] == [
            {"name": "search_datasets", "description": "Search."}
        ]
        # Not saved, and not cached under a credential no row will carry.
        assert seen == {"url": MCP["url"], "secret": "token", "remember": False}
        assert listed == []

    database(scenario)


def test_an_unsaved_mcp_tool_without_an_address_says_so(database):
    async def scenario():
        async with client() as api:
            result = (await api.post("/tools/test", json={"kind": "mcp"})).json()

        assert result == {"ok": False, "error": "no_url", "functions": None}

    database(scenario)
