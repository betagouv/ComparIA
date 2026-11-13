"""
The selection modes panel: what it may save, the guards that keep the arena
able to draw, the preview and the templates.
"""

import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

import utils.storage.redis as redis_storage  # noqa: E402
from backend.admin.selection_modes import admin_selection_modes_router  # noqa: E402
from backend.admin.selection_modes import services  # noqa: E402
from backend.admin.selection_modes.templates import TEMPLATES  # noqa: E402
from backend.llms.data import LLMsData  # noqa: E402
from backend.utils.locale import LocalesSettings  # noqa: E402
from tests.arena.modes import SEEDED  # noqa: E402
from tests.llms.test_selection_engine import llm  # noqa: E402
from utils.database.models import SelectionMode, SelectionModeUpsert  # noqa: E402
from utils.database.session import get_session  # noqa: E402

SMALL = llm("small", params=8)
SMALL2 = llm("small2", params=20, arena_tools=False)
BIG = llm("big", params=500)
LLMS = LLMsData.model_construct(all={m.id: m for m in [SMALL, SMALL2, BIG]})
MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "utils/database/alembic/versions/da69fc86f2ea_add_selection_modes_and_llm_fields.py"
)
MESSAGES_DIR = Path(__file__).resolve().parents[2] / "frontend/locales/messages"


@pytest.fixture(autouse=True)
def stubs(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = SimpleNamespace(invalidations=0)

    def no_redis():
        raise ConnectionError("no redis in these tests")

    async def get_llms_data():
        return LLMS

    async def get_offered_tools():
        return [SimpleNamespace(key="web_search")]

    async def get_locales_settings():
        return LocalesSettings(default="en", enabled=["en", "fr"])

    def invalidate_cache(_key):
        state.invalidations += 1

    monkeypatch.setattr(redis_storage, "get_redis_client", no_redis)
    monkeypatch.setattr(services, "get_llms_data", get_llms_data)
    monkeypatch.setattr(services, "get_offered_tools", get_offered_tools)
    monkeypatch.setattr(services, "get_locales_settings", get_locales_settings)
    monkeypatch.setattr(services, "get_ranking", lambda: None)
    monkeypatch.setattr(services, "invalidate_cache", invalidate_cache)
    return state


def client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(admin_selection_modes_router)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin"
    )


def mode(key: str, **fields) -> dict:
    return {"key": key, "label": {"en": key.title()}, "icon": "i-ri-dice-line"} | fields


async def create(api, key: str, **fields) -> dict:
    response = await api.post("/selection-modes", json=mode(key, **fields))
    assert response.status_code == 200, response.text
    return response.json()


async def listed(api) -> list[dict]:
    return (await api.get("/selection-modes")).json()


def test_a_mode_is_created_at_the_end_with_its_viability(database, stubs):
    async def scenario():
        async with client() as api:
            first = await create(api, "random")
            second = await create(api, "big", pool_a={"params_min": 100})
            third = await create(api, "huge", pool_a={"params_min": 10_000})
            return first, second, third, await listed(api)

    first, second, third, modes = database(scenario)
    assert (first["position"], second["position"]) == (0, 1)
    assert first["is_default"] is True and second["is_default"] is False
    assert first["viability"] == {
        "viable": True,
        "pool_a_size": 3,
        "pool_b_size": 3,
        "pairs": 3,
        "warnings": [],
    }
    assert second["viability"]["viable"] is False
    assert second["viability"]["warnings"] == ["no_valid_pair"]
    assert third["viability"]["warnings"] == ["pool_a_empty"]
    assert [m["key"] for m in modes] == ["random", "big", "huge"]
    assert stubs.invalidations == 3


@pytest.mark.parametrize(
    "body",
    [
        mode("Bad Key"),
        mode("x", icon="dice"),
        # A Remix icon, but not one the frontend builds: it would show a square.
        mode("x", icon="i-ri-alarm-line"),
        mode("x", label={"en": " "}),
        mode("x", tools_policy="forced"),
        mode("x", starts_at="2026-02-01T00:00:00", ends_at="2026-01-01T00:00:00"),
        mode("x", pool_a={"params_min": 10, "params_max": 1}),
        mode("x", visitor_picks=3),
    ],
)
def test_a_mode_that_cannot_work_is_refused(database, body):
    async def scenario():
        async with client() as api:
            return await api.post("/selection-modes", json=body)

    response = database(scenario)
    assert response.status_code == 422, response.text


def test_a_label_in_the_default_language_is_required(database):
    async def scenario():
        async with client() as api:
            return await api.post(
                "/selection-modes", json=mode("x", label={"fr": "Aléatoire"})
            )

    response = database(scenario)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "label_missing_default_locale"


def test_keys_are_unique_and_never_change(database):
    async def scenario():
        async with client() as api:
            saved = await create(api, "random")
            duplicate = await api.post("/selection-modes", json=mode("random"))
            renamed = await api.put(
                f"/selection-modes/{saved['id']}", json=mode("other")
            )
            relabelled = await api.put(
                f"/selection-modes/{saved['id']}",
                json=mode("random", label={"en": "Anything"}),
            )
            missing = await api.put(f"/selection-modes/{uuid.uuid4()}", json=mode("x"))
            return duplicate, renamed, relabelled, missing

    duplicate, renamed, relabelled, missing = database(scenario)
    assert (duplicate.status_code, duplicate.json()["detail"]) == (
        409,
        "mode_key_taken",
    )
    assert (renamed.status_code, renamed.json()["detail"]) == (
        400,
        "mode_key_immutable",
    )
    assert relabelled.json()["label"] == {"en": "Anything"}
    assert (missing.status_code, missing.json()["detail"]) == (404, "mode_not_found")


def test_one_default_at_a_time(database):
    async def scenario():
        async with client() as api:
            await create(api, "a")
            b = await create(api, "b")
            await api.put(
                f"/selection-modes/{b['id']}", json=mode("b", is_default=True)
            )
            after_switch = {m["key"]: m["is_default"] for m in await listed(api)}
            await api.put(f"/selection-modes/{b['id']}", json=mode("b", enabled=False))
            after_disable = {m["key"]: m["is_default"] for m in await listed(api)}
            return after_switch, after_disable

    after_switch, after_disable = database(scenario)
    assert after_switch == {"a": False, "b": True}
    # A disabled mode cannot be the default: it moves to the first enabled one.
    assert after_disable == {"a": True, "b": False}


def test_a_new_default_takes_over_without_tripping_the_index(database):
    async def scenario():
        async with client() as api:
            await create(api, "a")
            await create(api, "b", is_default=True)
            return {m["key"]: m["is_default"] for m in await listed(api)}

    assert database(scenario) == {"a": False, "b": True}


def test_the_database_refuses_a_second_default(database):
    async def scenario():
        async with get_session() as session:
            for key in ("a", "b"):
                session.add(
                    SelectionMode(
                        key=key,
                        label={"en": key},
                        icon="i-ri-dice-line",
                        is_default=True,
                    )
                )
            await session.commit()

    with pytest.raises(IntegrityError):
        database(scenario)


def test_two_admins_choosing_a_default_at_once_get_a_conflict(database, monkeypatch):
    read_rows = services._rows

    async def rows_then_other_admin(session):
        rows = await read_rows(session)
        # Another admin makes "c" the default once this request has read the
        # rows, and before it writes.
        async with get_session() as other:
            for row in await read_rows(other):
                row.is_default = row.key == "c"
                other.add(row)
                await other.flush()
            await other.commit()
        return rows

    async def scenario():
        async with client() as api:
            await create(api, "a")
            b = await create(api, "b")
            await create(api, "c")
            monkeypatch.setattr(services, "_rows", rows_then_other_admin)
            response = await api.put(
                f"/selection-modes/{b['id']}", json=mode("b", is_default=True)
            )
            monkeypatch.setattr(services, "_rows", read_rows)
            return response, {m["key"]: m["is_default"] for m in await listed(api)}

    response, defaults = database(scenario)
    assert (response.status_code, response.json()["detail"]) == (
        409,
        "default_mode_changed",
    )
    assert defaults == {"a": False, "b": False, "c": True}


def test_the_last_enabled_mode_cannot_go(database):
    async def scenario():
        async with client() as api:
            only = await create(api, "only")
            off = await create(api, "off", enabled=False)
            disable = await api.put(
                f"/selection-modes/{only['id']}", json=mode("only", enabled=False)
            )
            delete = await api.delete(f"/selection-modes/{only['id']}")
            delete_off = await api.delete(f"/selection-modes/{off['id']}")
            other = await create(api, "other")
            delete_now = await api.delete(f"/selection-modes/{only['id']}")
            return disable, delete, delete_off, delete_now, await listed(api), other

    disable, delete, delete_off, delete_now, modes, _other = database(scenario)
    assert (disable.status_code, disable.json()["detail"]) == (400, "last_enabled_mode")
    assert (delete.status_code, delete.json()["detail"]) == (400, "last_enabled_mode")
    assert delete_off.status_code == 204
    assert delete_now.status_code == 204
    # The default went with the deleted mode and moved to the one left.
    assert [(m["key"], m["is_default"]) for m in modes] == [("other", True)]


def test_the_menu_order_is_written_in_one_request(database):
    async def scenario():
        async with client() as api:
            a, b, c = [await create(api, key) for key in "abc"]
            reordered = await api.post(
                "/selection-modes/reorder", json={"ids": [c["id"], a["id"]]}
            )
            unknown = await api.post(
                "/selection-modes/reorder", json={"ids": [str(uuid.uuid4())]}
            )
            return reordered.json(), unknown

    modes, unknown = database(scenario)
    assert [(m["key"], m["position"]) for m in modes] == [("c", 0), ("a", 1), ("b", 2)]
    assert (unknown.status_code, unknown.json()["detail"]) == (404, "mode_not_found")


def test_the_preview_draws_like_the_arena_without_saving(database):
    async def scenario():
        async with client() as api:
            # A form still being filled in: no key, no label.
            preview = await api.post(
                "/selection-modes/preview",
                json={
                    "pool_a": {"params_min": 100},
                    "pool_b": {"params_max": 60},
                    "tools_policy": "forced",
                    "tool_keys": ["web_search", "datagouv"],
                },
            )
            return preview, await listed(api)

    preview, modes = database(scenario)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert [m["name"] for m in body["pool_a"]] == ["big"]
    assert {m["name"] for m in body["pool_b"]} == {"small", "small2"}
    assert body["viability"]["pairs"] == 2
    assert set(body["viability"]["warnings"]) == {
        "unknown_tool_keys",
        "tool_not_offered",
    }
    # A system with its own tools is flagged, so the admin knows it gets none.
    assert {m["name"]: m["arena_tools"] for m in body["pool_b"]} == {
        "small": True,
        "small2": False,
    }
    assert len(body["sample_draws"]) == 5
    # Pool A's model first, whatever side the draw put it on.
    for a, b in body["sample_draws"]:
        assert a["name"] == "big" and b["name"] in {"small", "small2"}
    assert modes == []


def test_a_preview_with_no_valid_pair_draws_nothing(database):
    async def scenario():
        async with client() as api:
            return await api.post(
                "/selection-modes/preview", json={"pool_a": {"params_min": 100}}
            )

    body = database(scenario).json()
    assert body["sample_draws"] == []
    assert body["viability"]["warnings"] == ["no_valid_pair"]


def test_every_template_fills_a_mode_that_can_be_saved(database):
    async def scenario():
        async with client() as api:
            return (await api.get("/selection-modes/templates")).json()

    templates = database(scenario)
    assert len(templates) == len(TEMPLATES) == 12
    assert len({template["id"] for template in templates}) == 12
    for template in templates:
        assert set(template) == {"id", "mode"}
        SelectionModeUpsert.model_validate(template["mode"])


def test_every_template_has_a_title_and_description_in_english_and_french():
    for locale in ("en", "fr"):
        messages = json.loads((MESSAGES_DIR / f"{locale}.json").read_text())
        texts = messages["admin"]["selectionModes"]["templates"]
        for template in TEMPLATES:
            assert texts[template.id]["title"] and texts[template.id]["description"]


def test_the_form_schema_is_served(database):
    async def scenario():
        async with client() as api:
            return (await api.get("/selection-modes/schemas")).json()

    schema = database(scenario)["selection_mode"]
    assert "pool_a" in schema["properties"] and "ModelFilter" in schema["$defs"]


# The seed


def test_the_seeded_modes_are_valid_rows_with_the_old_rules():
    spec = importlib.util.spec_from_file_location("seed", MIGRATION)
    assert spec and spec.loader
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)

    for key, icon, visitor_picks, pool_a, pool_b in seed._MODES:
        row = SelectionModeUpsert.model_validate(
            {
                "key": key,
                "icon": icon,
                "visitor_picks": visitor_picks,
                "pool_a": pool_a,
                "pool_b": pool_b,
                **seed._TEXTS[key],
            }
        )
        assert {"en", "fr"} <= set(row.label) and row.short_label and row.description
        # The arena tests stand in for the database with the same rules.
        stand_in = SEEDED[key]
        assert (row.visitor_picks, row.pool_a, row.pool_b) == (
            stand_in.visitor_picks,
            stand_in.pool_a,
            stand_in.pool_b,
        )
