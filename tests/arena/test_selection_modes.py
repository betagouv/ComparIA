"""
Selection modes as the arena sees them: which ones a visitor is offered, and
what a first message gets under each, tools included. The modes live in the
database; the models and tools are stubs.
"""

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

# isort: off
# Before the router, whose imports go round in a circle otherwise.
import utils.database.models  # noqa: E402,F401

# isort: on
import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import backend.arena.streaming as streaming  # noqa: E402
import utils.storage.redis as redis_storage  # noqa: E402
from backend.llms.data import LLMsData  # noqa: E402
from backend.selection_modes import services  # noqa: E402
from backend.utils.locale import LocalesSettings  # noqa: E402
from tests.arena.test_ratelimit import default_prompt_check  # noqa: E402
from tests.arena.test_stream_event_loop import (  # noqa: E402
    comparison_between,
    fake_models,
)
from tests.llms.test_selection_engine import llm  # noqa: E402
from utils.database.models import (  # noqa: E402
    SelectionMode,
    SelectionModeUpsert,
)
from utils.database.models.utils import utc_now  # noqa: E402
from utils.database.session import get_session  # noqa: E402

SMALL = llm("small", params=8)
SMALL2 = llm("small2", params=20)
BIG = llm("big", params=500, tags=["legal"])
LOCKED = llm("locked", params=30, custom_selectable=False, tags=["legal"])
LLMS = LLMsData.model_construct(
    all={model.id: model for model in [SMALL, SMALL2, BIG, LOCKED]}
)
OFFERED_TOOLS = ["web_search", "datagouv"]


@pytest.fixture(autouse=True)
def stubs(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Models, tools and locales as stubs, and no Redis, so that the mode
    cache never outlives a test."""
    state = SimpleNamespace(tool_lookups=0)

    def no_redis():
        raise ConnectionError("no redis in these tests")

    async def get_llms_data():
        return LLMS

    async def get_offered_tools():
        state.tool_lookups += 1
        return [SimpleNamespace(key=key) for key in OFFERED_TOOLS]

    async def get_locales_settings():
        return LocalesSettings(default="en", enabled=["en", "fr"])

    monkeypatch.setattr(redis_storage, "get_redis_client", no_redis)
    monkeypatch.setattr(services, "get_llms_data", get_llms_data)
    monkeypatch.setattr(services, "get_offered_tools", get_offered_tools)
    monkeypatch.setattr(services, "get_locales_settings", get_locales_settings)
    monkeypatch.setattr(services, "get_ranking", lambda: None)
    return state


async def add_modes(*modes: dict[str, Any]) -> None:
    async with get_session() as session:
        for position, fields in enumerate(modes):
            session.add(
                SelectionMode.model_validate(
                    {
                        "label": {"en": fields["key"].title()},
                        "icon": "i-ri-dice-line",
                        "position": position,
                    }
                    | fields
                )
            )
        await session.commit()


# What a visitor is offered


def test_only_modes_meant_for_the_visitor_now_are_offered(database):
    now = utc_now()

    async def scenario():
        await add_modes(
            {"key": "random", "is_default": True},
            {"key": "off", "enabled": False},
            {"key": "later", "starts_at": now + timedelta(days=1)},
            {"key": "over", "ends_at": now - timedelta(days=1)},
            {"key": "running", "starts_at": now - timedelta(days=1)},
            {"key": "french", "locales": ["fr"]},
            {"key": "pix", "cohorts": ["pix"]},
            {"key": "empty", "pool_a": {"params_min": 10_000}},
        )
        english = await services.get_public_modes("en", "")
        french_pix = await services.get_public_modes("fr", "other,pix")
        return [m.key for m in english], [m.key for m in french_pix]

    english, french_pix = database(scenario)
    assert english == ["random", "running"]
    assert french_pix == ["random", "running", "french", "pix"]


def test_a_blind_mode_keeps_its_pools_to_itself(database):
    async def scenario():
        await add_modes(
            {"key": "legal", "pool_a": {"tags": ["legal"]}, "tools_policy": "none"},
            {"key": "pick-legal", "pool_a": {"tags": ["legal"]}, "visitor_picks": 1},
        )
        return await arena_router.get_selection_modes("en", None)

    blind, picks = database(scenario)
    assert blind.llm_ids is None
    assert blind.tool_keys == []
    # The locked model is listed so the arena can grey it; the draw refuses it.
    assert picks.llm_ids == [BIG.id, LOCKED.id]
    assert picks.visitor_picks == 1
    dumped = blind.model_dump()
    assert "pool_a" not in dumped and "tags" not in str(dumped)


def test_a_two_pick_mode_with_two_pools_tells_the_picker_each_pool(database):
    async def scenario():
        await add_modes(
            {
                "key": "split",
                "visitor_picks": 2,
                "pool_a": {"params_min": 100},
                "pool_b": {"params_max": 60},
            },
            {"key": "one-pick", "visitor_picks": 1, "pool_b": {"params_max": 60}},
            {"key": "blind", "pool_b": {"params_max": 60}},
        )
        return await services.get_public_modes("en", None)

    split, one_pick, blind = database(scenario)
    assert split.llm_ids_a == [BIG.id]
    assert split.llm_ids_b == [SMALL.id, SMALL2.id, LOCKED.id]
    # One pick is drawn against, and a blind mode tells nothing.
    assert one_pick.llm_ids_a is None and one_pick.llm_ids_b is None
    assert blind.llm_ids_a is None and blind.llm_ids_b is None


def test_exactly_one_mode_on_offer_is_the_default(database):
    async def scenario():
        await add_modes(
            {"key": "first"},
            {"key": "hidden-default", "is_default": True, "cohorts": ["pix"]},
            {"key": "second"},
        )
        anyone = await services.get_public_modes("en", "")
        pix = await services.get_public_modes("en", "pix")
        return anyone, pix

    anyone, pix = database(scenario)
    assert [m.key for m in anyone if m.is_default] == ["first"]
    assert [m.key for m in pix if m.is_default] == ["hidden-default"]


def test_labels_are_picked_for_the_locale(database):
    async def scenario():
        await add_modes(
            {
                "key": "random",
                "label": {"en": "Random", "fr": "Aléatoire"},
                "short_label": {"en": "Random models"},
                "description": {"fr": "Deux modèles au hasard"},
            },
        )
        return (
            (await services.get_public_modes("fr", ""))[0],
            (await services.get_public_modes("en", ""))[0],
        )

    french, english = database(scenario)
    assert (french.label, french.short_label) == ("Aléatoire", "Random models")
    assert french.description == "Deux modèles au hasard"
    # No short label in English either: it falls back on the label.
    english_short = english.short_label
    assert english.label == "Random" and english_short == "Random models"


def test_the_tools_shown_follow_the_policy(database):
    async def scenario():
        await add_modes(
            {"key": "visitor"},
            {"key": "narrow", "tool_keys": ["datagouv", "gone"]},
            {"key": "forced", "tools_policy": "forced", "tool_keys": ["web_search"]},
            {"key": "dead", "tools_policy": "forced", "tool_keys": ["gone"]},
            {"key": "none", "tools_policy": "none", "tool_keys": ["web_search"]},
        )
        return {m.key: m.tool_keys for m in await services.get_public_modes("en", "")}

    assert database(scenario) == {
        "visitor": OFFERED_TOOLS,
        "narrow": ["datagouv"],
        "forced": ["web_search"],
        "none": [],
    }


# A first message


def first_message(**fields: Any):
    """Run add_first_text up to the comparison it would create."""
    created = []

    async def create_comparison(comparison):
        created.append(comparison)
        raise HTTPException(status_code=503, detail="stop here")

    async def terms_version(**_ids):
        return "2026.07"

    async def run_checks(*_args, **_kwargs):
        return None

    async def get_llms_data():
        return LLMS

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/arena/add_first_text",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )
    patches = {
        "create_comparison": create_comparison,
        "get_current_terms_acceptance_version": terms_version,
        "run_checks": run_checks,
        "get_llms_data": get_llms_data,
        "get_prompt_check": default_prompt_check,
        "charge_budget": lambda *_args: None,
        "reserve_conversation": lambda *_args, **_kwargs: True,
        "release_conversation": lambda *_args: None,
    }
    originals = {name: getattr(arena_router, name) for name in patches}
    original_captcha = arena_models.verify_altcha_token
    try:
        for name, value in patches.items():
            setattr(arena_router, name, value)
        arena_models.verify_altcha_token = lambda _token: (True, None)
        body = arena_models.AddFirstTextBody(
            prompt_value="Bonjour, explique la photosynthese",
            altcha_token="valid",
            **{"cohorts": ""} | fields,
        )
        try:
            asyncio.run(arena_router.add_first_text(body, None, "b" * 64, request))
        except HTTPException as error:
            if error.status_code != 503:
                return error
    finally:
        for name, value in originals.items():
            setattr(arena_router, name, value)
        arena_models.verify_altcha_token = original_captcha
    return created[0]


def in_database(database, modes: list[dict[str, Any]], **fields: Any):
    async def scenario():
        await add_modes(*modes)

    database(scenario)
    return first_message(**fields)


def test_a_mode_without_tools_gets_none_whatever_the_client_sends(database, stubs):
    created = in_database(
        database,
        [{"key": "legal", "tools_policy": "none", "pool_a": {"tags": ["legal"]}}],
        mode="legal",
        tools=["web_search", "datagouv"],
    )
    assert created.enabled_tools == []
    assert created.mode == "legal"
    # Drawn from the pool, the locked model included: the lock only stops picks.
    assert {created.llm_id_a, created.llm_id_b} == {BIG.id, LOCKED.id}
    # The list the client sent is not even looked at.
    assert stubs.tool_lookups == 0


def test_a_mode_that_forces_tools_gets_them_whatever_the_client_sends(database):
    created = in_database(
        database,
        [{"key": "web", "tools_policy": "forced", "tool_keys": ["web_search"]}],
        mode="web",
        tools=["datagouv"],
    )
    assert created.enabled_tools == ["web_search"]


def test_a_visitor_mode_keeps_only_the_tools_it_allows(database):
    created = in_database(
        database,
        [{"key": "narrow", "tool_keys": ["datagouv"]}],
        mode="narrow",
        tools=["web_search", "datagouv", "rogue"],
    )
    assert created.enabled_tools == ["datagouv"]


def test_a_missing_mode_runs_the_default(database):
    created = in_database(
        database,
        [{"key": "first"}, {"key": "chosen", "is_default": True}],
    )
    assert created.mode == "chosen"


def test_with_nothing_on_offer_a_first_message_gets_a_plain_draw(database):
    created = in_database(
        database,
        [
            {"key": "pix", "cohorts": ["pix"], "is_default": True},
            {"key": "off", "enabled": False},
        ],
        cohorts="",
    )
    assert created.mode == "random"
    assert created.enabled_tools == []
    assert created.llm_id_a != created.llm_id_b
    assert {created.llm_id_a, created.llm_id_b} <= {m.id for m in LLMS.all.values()}


@pytest.mark.parametrize(
    "mode, fields",
    [
        ({"key": "off", "enabled": False}, {}),
        ({"key": "pix", "cohorts": ["pix"]}, {"cohorts": "other"}),
        ({"key": "french", "locales": ["fr"]}, {"locale": "en"}),
        ({"key": "over", "ends_at": "2020-01-01T00:00:00"}, {}),
        ({"key": "empty", "pool_a": {"params_min": 10_000}}, {}),
        (
            {"key": "dead", "tools_policy": "forced", "tool_keys": ["gone"]},
            {},
        ),
    ],
)
def test_a_mode_not_on_offer_is_refused(database, mode, fields):
    error = in_database(database, [{"key": "random"}, mode], mode=mode["key"], **fields)
    assert (error.status_code, error.detail) == (400, "mode_unavailable")


def test_an_unknown_mode_is_refused(database):
    error = in_database(database, [{"key": "random"}], mode="nope")
    assert (error.status_code, error.detail) == (400, "mode_unavailable")


def test_a_cohort_mode_is_accepted_for_its_cohort(database):
    created = in_database(
        database, [{"key": "pix", "cohorts": ["pix"]}], mode="pix", cohorts="pix"
    )
    assert created.mode == "pix"


def test_a_comparison_records_only_cohorts_someone_set_up(database):
    created = in_database(
        database,
        [{"key": "random"}, {"key": "acme", "cohorts": ["acme"]}],
        cohorts="zzz-from-a-link,pix,acme,<script>",
    )
    # pix is known to the code, acme is named by a mode, the rest is dropped.
    assert created.cohorts == "acme,pix"


def test_a_mode_cohort_must_be_one_a_visitor_can_declare():
    with pytest.raises(ValueError):
        SelectionModeUpsert.model_validate(
            {"key": "x", "label": {"en": "X"}, "icon": "i-ri-dice-line"}
            | {"cohorts": ["a,b"]}
        )


@pytest.mark.parametrize(
    "mode, picks",
    [
        # Outside the pool.
        ({"key": "small", "visitor_picks": 2, "pool_a": {"params_max": 60}}, [BIG]),
        # Locked out of picks.
        ({"key": "pick", "visitor_picks": 2}, [LOCKED]),
        # A blind mode takes no pick.
        ({"key": "blind"}, [SMALL]),
    ],
)
def test_a_pick_the_mode_does_not_allow_is_refused(database, mode, picks):
    error = in_database(
        database,
        [mode],
        mode=mode["key"],
        custom_models_selection=[str(model.id) for model in picks],
    )
    assert (error.status_code, error.detail) == (400, "model_unavailable")


def test_a_pick_inside_the_pool_is_kept(database):
    created = in_database(
        database,
        [{"key": "small", "visitor_picks": 1, "pool_a": {"params_max": 60}}],
        mode="small",
        custom_models_selection=[str(SMALL.id)],
    )
    assert SMALL.id in (created.llm_id_a, created.llm_id_b)
    assert {created.llm_id_a, created.llm_id_b} <= {SMALL.id, SMALL2.id, LOCKED.id}
    assert created.custom_models_selection == (str(SMALL.id),)


def test_a_pick_mode_with_its_own_pool_keeps_its_key_when_nothing_is_picked(database):
    created = in_database(
        database,
        [
            {"key": "random", "is_default": True},
            {"key": "pick-small", "visitor_picks": 2, "pool_a": {"params_max": 60}},
        ],
        mode="pick-small",
    )
    # Its draw is not the default mode's, so calling it "random" would be false.
    assert created.mode == "pick-small"


def test_a_pick_mode_drawing_like_the_default_is_stored_as_the_default(database):
    created = in_database(
        database,
        [{"key": "random", "is_default": True}, {"key": "custom", "visitor_picks": 2}],
        mode="custom",
    )
    assert created.mode == "random"
    assert created.custom_models_selection is None


# Later turns


def test_later_turns_cannot_bring_tools_of_their_own():
    with_tools = {"tools": ["web_search"], "altcha_token": "valid"}
    original = arena_models.verify_altcha_token
    arena_models.verify_altcha_token = lambda _token: (True, None)
    try:
        text = arena_models.AddTextBody(message="Et ensuite ?", **with_tools)
        retry = arena_models.RetryBody(**with_tools)
    finally:
        arena_models.verify_altcha_token = original
    assert not hasattr(text, "tools") and not hasattr(retry, "tools")


@pytest.mark.parametrize("stored", [[], ["web_search"]])
def test_every_turn_runs_with_the_tools_stored_on_the_comparison(monkeypatch, stored):
    resolved: list[list[str]] = []
    offered: list[Any] = []

    async def resolve_tools(keys):
        resolved.append(list(keys))
        return [SimpleNamespace(name=key) for key in keys]

    fake_models(monkeypatch, {"fast": 0.0, "slow": 0.0}, set())
    original = streaming.bot_response_async

    def bot_response_async(
        pos, llm, turn, turn_index, messages, request=None, tools=None
    ):
        offered.append([tool.name for tool in tools or []])
        return original(pos, llm, turn, turn_index, messages, request, tools)

    monkeypatch.setattr(streaming, "resolve_tools", resolve_tools)
    monkeypatch.setattr(streaming, "bot_response_async", bot_response_async)
    comparison = comparison_between("fast", "slow")
    comparison.enabled_tools = stored

    async def run():
        async for _event in streaming.stream_comparison_messages(
            comparison, comparison.turns[-1]
        ):
            pass

    asyncio.run(run())
    assert resolved == [stored]
    assert offered == [stored, stored]
