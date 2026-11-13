"""
The draw behind every selection mode: which models a filter keeps, which pairs
a mode may draw, and what the admin is warned about. No database: the engine
takes everything it reads as arguments.
"""

import random
from collections import Counter
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4, uuid5

import pytest

from backend.errors import NoValidPairError, UnavailableLLMsSelectionError
from backend.llms.data import LLMsData
from backend.llms.models import LLMDataEnabled
from backend.llms.selection import (
    ToolsOnOffer,
    allowed_tools,
    draw_pair,
    enabled_tools,
    filter_pool,
    picker_llm_ids,
    replacement_pool,
    viability,
)
from utils.database.models import ModelFilter, SelectionModeRules

TODAY = date(2026, 11, 12)
NAMESPACE = UUID("0f7e1d2c-3b4a-4596-8877-665544332211")
LAB_A, LAB_B = uuid4(), uuid4()
LICENSE_OPEN, LICENSE_CLOSED = uuid4(), uuid4()
DRAWS = 200


def llm(name: str, **overrides: Any) -> LLMDataEnabled:
    fields: dict[str, Any] = {
        "id": uuid5(NAMESPACE, name),
        "status": "enabled",
        "name": name,
        "human_id": name,
        "api_model_id": name,
        "rate_limited": False,
        "custom_selectable": True,
        "lab_id": LAB_A,
        "lab": {"name": "Lab", "logo": None, "origin_country": "FR"},
        "license_id": LICENSE_OPEN,
        "license": {
            "kind": "open-weights",
            "name": "Apache 2.0",
            "reuse": True,
            "commercial_use": True,
        },
        "endpoint": {"name": "Test", "api_type": "openai", "api_key": "k"},
        "release_date": TODAY - timedelta(days=30),
        "public_weights": True,
        "public_training_data": False,
        "public_training_code": False,
        "eu_hostable": True,
        "arch": "dense",
        "params": 10,
        "inputs": ["text"],
        "price_in": 0.1,
        "price_out": 0.2,
        "tags": [],
    }
    return LLMDataEnabled.model_validate(fields | overrides)


def catalogue(*llms: LLMDataEnabled) -> LLMsData:
    return LLMsData.model_construct(all={model.id: model for model in llms})


def ids(*names: str) -> set[UUID]:
    return {uuid5(NAMESPACE, name) for name in names}


def ranking(**n_matches: tuple[int, int]) -> Any:
    """{name: (rank, n_match)}, shaped like the cached ranking: plain dicts."""
    return SimpleNamespace(
        rankings={
            str(uuid5(NAMESPACE, name)): {"rank": rank, "n_match": n_match}
            for name, (rank, n_match) in n_matches.items()
        }
    )


def draws(mode: SelectionModeRules, llms: LLMsData, n: int = DRAWS, **kwargs):
    rng = random.Random(42)
    return [draw_pair(mode, llms, rng=rng, today=TODAY, **kwargs) for _ in range(n)]


# Filters


SMALL = llm("small", params=8)
MID = llm("mid", params=70, lab_id=LAB_B, tags=["legal"])
BIG = llm("big", params=500, tags=["legal", "sovereign"], public_weights=False)
CATALOGUE = [SMALL, MID, BIG]


@pytest.mark.parametrize(
    "f, kept",
    [
        (ModelFilter(), {"small", "mid", "big"}),
        (ModelFilter(llm_ids=[SMALL.id, BIG.id]), {"small", "big"}),
        (ModelFilter(exclude_llm_ids=[SMALL.id]), {"mid", "big"}),
        (ModelFilter(lab_ids=[LAB_B]), {"mid"}),
        (ModelFilter(exclude_lab_ids=[LAB_B]), {"small", "big"}),
        (ModelFilter(tags=["legal"]), {"mid", "big"}),
        (ModelFilter(tags=["Legal", "sovereign"]), {"mid", "big"}),
        (ModelFilter(tags=["legal", "sovereign"], tags_match="all"), {"big"}),
        (ModelFilter(exclude_tags=["sovereign"]), {"small", "mid"}),
        (ModelFilter(public_weights=True), {"small", "mid"}),
        (ModelFilter(public_weights=False), {"big"}),
        (ModelFilter(size_classes=["XS"]), {"small"}),
        (ModelFilter(params_min=70), {"mid", "big"}),
        (ModelFilter(params_max=70), {"small", "mid"}),
        (ModelFilter(params_min=60, params_max=100), {"mid"}),
    ],
)
def test_a_filter_keeps_the_models_that_pass_every_set_field(f, kept):
    assert set(filter_pool(CATALOGUE, f, today=TODAY)) == ids(*kept)


def test_the_remaining_filter_fields():
    old = llm("old", release_date=date(2024, 1, 1), price_out=30.0)
    recent = llm("recent", release_date=TODAY - timedelta(days=10))
    vision = llm("vision", inputs=["text", "image"], arch="moe", active_params=2)
    closed = llm(
        "closed",
        license_id=LICENSE_CLOSED,
        eu_hostable=False,
        rate_limited=True,
    )
    llms = [old, recent, vision, closed]

    def kept(**f):
        return {llm_id for llm_id in filter_pool(llms, ModelFilter(**f), today=TODAY)}

    assert kept(license_ids=[LICENSE_CLOSED]) == ids("closed")
    assert kept(eu_hostable=False) == ids("closed")
    assert kept(archs=["moe"]) == ids("vision")
    assert kept(inputs=["image"]) == ids("vision")
    assert kept(inputs=["text", "image"]) == ids("vision")
    assert kept(released_after=date(2025, 1, 1)) == ids("recent", "vision", "closed")
    assert kept(released_before=date(2025, 1, 1)) == ids("old")
    assert kept(released_within_days=15) == ids("recent")
    assert kept(price_out_max=1.0) == ids("recent", "vision", "closed")
    assert kept(rate_limited=True) == ids("closed")
    assert kept(rate_limited=False) == ids("old", "recent", "vision")


def test_energy_classes_follow_the_computed_class():
    classes = {model.id: model.energy_class for model in CATALOGUE}
    for energy_class in set(classes.values()):
        assert set(
            filter_pool(CATALOGUE, ModelFilter(energy_classes=[energy_class]))
        ) == {llm_id for llm_id, c in classes.items() if c == energy_class}


def test_top_ranked_keeps_the_best_and_never_an_unranked_model():
    ranks = ranking(small=(3, 10), mid=(1, 10))
    best_one = filter_pool(CATALOGUE, ModelFilter(top_ranked=1), ranks)
    best_five = filter_pool(CATALOGUE, ModelFilter(top_ranked=5), ranks)
    no_ranking = filter_pool(CATALOGUE, ModelFilter(top_ranked=5), None)

    assert set(best_one) == ids("mid")
    assert set(best_five) == ids("small", "mid")
    assert no_ranking == []


@pytest.mark.parametrize(
    "f",
    [
        {"params_min": 10, "params_max": 5},
        {"released_after": "2026-01-02", "released_before": "2026-01-01"},
        {"tags": ["not a tag!"]},
        {"top_ranked": 0},
    ],
)
def test_an_incoherent_filter_is_refused(f):
    with pytest.raises(ValueError):
        ModelFilter(**f)


# Pairs


def test_two_different_models_always():
    llms = catalogue(*CATALOGUE)
    assert all(a != b for a, b in draws(SelectionModeRules(), llms))


@pytest.mark.parametrize(
    "pairing, allowed",
    [
        ("different_lab", lambda a, b: a.lab_id != b.lab_id),
        ("same_lab", lambda a, b: a.lab_id == b.lab_id),
        ("different_size_class", lambda a, b: a.size_class != b.size_class),
        ("same_size_class", lambda a, b: a.size_class == b.size_class),
    ],
)
def test_each_pairing_rule_holds_on_every_draw(pairing, allowed):
    models = [
        llm("a1", lab_id=LAB_A, params=8),
        llm("a2", lab_id=LAB_A, params=500),
        llm("a3", lab_id=LAB_A, params=9),
        llm("b1", lab_id=LAB_B, params=8),
    ]
    llms = catalogue(*models)
    pairs = draws(SelectionModeRules(pairing=pairing), llms)

    assert all(allowed(llms.enabled[a], llms.enabled[b]) for a, b in pairs)
    # Every allowed pair can come up, not only the first one found.
    allowed_pairs = {
        frozenset((a.id, b.id))
        for a in models
        for b in models
        if a.id != b.id and allowed(a, b)
    }
    assert {frozenset(pair) for pair in pairs} == allowed_pairs


def test_a_pairing_rule_that_cannot_be_met_fails_the_draw():
    llms = catalogue(llm("a1", lab_id=LAB_A), llm("a2", lab_id=LAB_A))
    with pytest.raises(NoValidPairError):
        draw_pair(SelectionModeRules(pairing="different_lab"), llms)


def test_the_picker_leaves_out_a_model_the_pairing_leaves_alone():
    llms = catalogue(
        llm("a1", lab_id=LAB_A), llm("a2", lab_id=LAB_A), llm("b1", lab_id=LAB_B)
    )
    mode = SelectionModeRules(visitor_picks=1, pairing="same_lab")
    assert set(picker_llm_ids(mode, llms)) == ids("a1", "a2")


def test_a_single_model_pool_fails_the_draw():
    llms = catalogue(SMALL, BIG)
    with pytest.raises(NoValidPairError):
        draw_pair(SelectionModeRules(pool_a=ModelFilter(params_max=60)), llms)


def test_sides_come_out_in_random_order():
    llms = catalogue(SMALL, BIG)
    mode = SelectionModeRules(
        pool_a=ModelFilter(params_min=100), pool_b=ModelFilter(params_max=60)
    )
    assert {pair[0] for pair in draws(mode, llms)} == {SMALL.id, BIG.id}


# The seeded modes draw as the hard-coded ones did


SEEDED_CATALOGUE = [
    llm("tiny", params=3),
    llm("small60", params=60),
    llm("mid80", params=80),
    llm("big100", params=100),
    llm("huge", params=600),
]


def test_seeded_small_models_draws_two_models_of_60b_or_less():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(pool_a=ModelFilter(params_max=60))
    for a, b in draws(mode, llms):
        assert {a, b} == ids("tiny", "small60")


def test_seeded_big_vs_small_draws_one_of_each():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(
        pool_a=ModelFilter(params_min=100), pool_b=ModelFilter(params_max=60)
    )
    for a, b in draws(mode, llms):
        params = sorted([llms.enabled[a].params, llms.enabled[b].params])
        assert params[0] <= 60 and params[1] >= 100


def test_seeded_random_draws_from_the_whole_catalogue():
    llms = catalogue(*SEEDED_CATALOGUE)
    drawn = {llm_id for pair in draws(SelectionModeRules(), llms) for llm_id in pair}
    assert drawn == set(llms.enabled)


# Visitor picks


def test_two_picks_are_the_pair_whatever_the_pairing():
    llms = catalogue(llm("a1", lab_id=LAB_A), llm("a2", lab_id=LAB_A))
    mode = SelectionModeRules(visitor_picks=2, pairing="different_lab")
    picks = list(ids("a1", "a2"))
    for pair in draws(mode, llms, picked=picks):
        assert set(pair) == set(picks)


def test_one_pick_gets_a_drawn_partner_that_honours_the_pairing():
    models = [
        llm("a1", lab_id=LAB_A),
        llm("a2", lab_id=LAB_A),
        llm("b1", lab_id=LAB_B),
    ]
    llms = catalogue(*models)
    mode = SelectionModeRules(visitor_picks=1, pairing="different_lab")
    for pair in draws(mode, llms, picked=[models[0].id]):
        assert set(pair) == {models[0].id, models[2].id}


def test_one_pick_in_pool_a_gets_its_partner_from_pool_b():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(
        visitor_picks=1,
        pool_a=ModelFilter(params_min=100),
        pool_b=ModelFilter(params_max=60),
    )
    (huge,) = ids("huge")
    for pair in draws(mode, llms, picked=[huge]):
        other = next(llm_id for llm_id in pair if llm_id != huge)
        assert llms.enabled[other].params <= 60


def test_two_picks_in_a_split_mode_take_one_model_from_each_pool():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(
        visitor_picks=2,
        pool_a=ModelFilter(params_min=100),
        pool_b=ModelFilter(params_max=60),
    )
    big_and_small = list(ids("huge", "tiny"))
    # Either order: the visitor does not know which pool is A.
    for picked in (big_and_small, big_and_small[::-1]):
        for pair in draws(mode, llms, picked=picked):
            assert set(pair) == set(big_and_small)
    with pytest.raises(UnavailableLLMsSelectionError, match="each pool"):
        draw_pair(mode, llms, picked=list(ids("tiny", "small60")))


@pytest.mark.parametrize(
    "mode, picked",
    [
        # Outside the pools.
        (
            SelectionModeRules(visitor_picks=2, pool_a=ModelFilter(params_max=60)),
            ["mid"],
        ),
        # More than the mode allows.
        (SelectionModeRules(visitor_picks=1), ["small", "mid"]),
        # A blind mode takes no pick at all.
        (SelectionModeRules(), ["small"]),
        # Twice the same model.
        (SelectionModeRules(visitor_picks=2), ["small", "small"]),
    ],
)
def test_a_pick_the_mode_does_not_allow_is_refused(mode, picked):
    llms = catalogue(*CATALOGUE)
    with pytest.raises(UnavailableLLMsSelectionError):
        draw_pair(mode, llms, picked=[uuid5(NAMESPACE, name) for name in picked])


def test_a_locked_or_unknown_pick_is_refused():
    locked = llm("locked", custom_selectable=False)
    llms = catalogue(SMALL, MID, locked)
    mode = SelectionModeRules(visitor_picks=2)
    with pytest.raises(UnavailableLLMsSelectionError, match="locked"):
        draw_pair(mode, llms, picked=[locked.id])
    with pytest.raises(UnavailableLLMsSelectionError, match="unavailable"):
        draw_pair(mode, llms, picked=[uuid4()])


# Unavailable models


def test_unavailable_models_are_left_out_when_the_pool_allows_it():
    llms = catalogue(*SEEDED_CATALOGUE)
    down = ids("tiny", "huge")
    for pair in draws(SelectionModeRules(), llms, unavailable=down):
        assert not set(pair) & down


def test_unavailable_models_come_back_when_nothing_else_is_left():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(pool_a=ModelFilter(params_max=60))
    pairs = draws(mode, llms, unavailable=ids("tiny"))
    assert all(set(pair) == ids("tiny", "small60") for pair in pairs)


# Sampling


def test_fewer_votes_favours_models_with_few_votes():
    llms = catalogue(*SEEDED_CATALOGUE)
    ranks = ranking(
        tiny=(1, 0), small60=(2, 10_000), mid80=(3, 10_000), big100=(4, 10_000)
    )
    counts = Counter(
        llm_id
        for pair in draws(
            SelectionModeRules(sampling="fewer_votes"), llms, ranking=ranks
        )
        for llm_id in pair
    )
    # 'huge' has no ranking data, so it counts as never voted on too.
    (tiny,), (huge,), (small60,) = ids("tiny"), ids("huge"), ids("small60")
    assert counts[tiny] > DRAWS * 0.8 and counts[huge] > DRAWS * 0.8
    assert counts[small60] < DRAWS * 0.1


def test_newest_favours_recent_models():
    models = [
        llm("new", release_date=TODAY),
        llm("new2", release_date=TODAY - timedelta(days=5)),
        llm("ancient", release_date=TODAY - timedelta(days=5 * 365)),
    ]
    counts = Counter(
        llm_id
        for pair in draws(SelectionModeRules(sampling="newest"), catalogue(*models))
        for llm_id in pair
    )
    (ancient,), (new,) = ids("ancient"), ids("new")
    assert counts[ancient] < DRAWS * 0.1 < counts[new]


def test_uniform_draws_every_model_about_as_often():
    llms = catalogue(*SEEDED_CATALOGUE)
    counts = Counter(
        llm_id for pair in draws(SelectionModeRules(), llms, n=1000) for llm_id in pair
    )
    # 2000 slots over 5 models.
    assert all(300 < count < 500 for count in counts.values())


# Replacement


def test_a_failing_big_model_is_replaced_from_the_big_pool():
    llms = catalogue(*SEEDED_CATALOGUE)
    mode = SelectionModeRules(
        pool_a=ModelFilter(params_min=100), pool_b=ModelFilter(params_max=60)
    )
    (huge,), (tiny,) = ids("huge"), ids("tiny")
    assert set(replacement_pool(mode, llms, huge, tiny)) == ids("big100")
    assert set(replacement_pool(mode, llms, tiny, huge)) == ids("small60")


def test_a_replacement_keeps_the_pair_valid():
    models = [
        llm("a1", lab_id=LAB_A),
        llm("a2", lab_id=LAB_A),
        llm("b1", lab_id=LAB_B),
        llm("b2", lab_id=LAB_B),
    ]
    llms = catalogue(*models)
    mode = SelectionModeRules(pairing="different_lab")
    failing, other = models[2].id, models[0].id
    assert set(replacement_pool(mode, llms, failing, other)) == ids("b2")


def test_a_replacement_never_returns_either_model():
    llms = catalogue(*SEEDED_CATALOGUE)
    (tiny,), (huge,) = ids("tiny"), ids("huge")
    pool = replacement_pool(SelectionModeRules(), llms, tiny, huge)
    assert tiny not in pool and huge not in pool and len(pool) == 3


# Viability


def test_viability_counts_pairs_and_names_what_is_wrong():
    llms = catalogue(*SEEDED_CATALOGUE)

    random_mode = viability(SelectionModeRules(), llms)
    assert random_mode.viable and random_mode.pairs == 10
    assert random_mode.warnings == []

    empty_b = viability(SelectionModeRules(pool_b=ModelFilter(params_min=10_000)), llms)
    assert not empty_b.viable and "pool_b_empty" in empty_b.warnings

    empty_a = viability(SelectionModeRules(pool_a=ModelFilter(params_min=10_000)), llms)
    assert not empty_a.viable and "pool_a_empty" in empty_a.warnings

    one_pair = viability(SelectionModeRules(pool_a=ModelFilter(params_max=60)), llms)
    assert one_pair.viable and one_pair.warnings == ["single_pair"]

    unknown = viability(
        SelectionModeRules(pool_a=ModelFilter(exclude_llm_ids=[uuid4()])), llms
    )
    assert unknown.viable and unknown.warnings == ["unknown_llm_ids"]


def test_a_pairing_rule_nothing_meets_is_not_viable():
    llms = catalogue(llm("a1", lab_id=LAB_A), llm("a2", lab_id=LAB_A))
    result = viability(SelectionModeRules(pairing="different_lab"), llms)
    assert not result.viable and result.warnings == ["no_valid_pair"]


def test_a_forced_tool_that_is_not_on_offer_makes_the_mode_not_viable():
    llms = catalogue(*SEEDED_CATALOGUE)
    tools = ToolsOnOffer(known={"web_search", "datagouv"}, offered={"datagouv"})
    forced = SelectionModeRules(tools_policy="forced", tool_keys=["web_search"])
    visitor = SelectionModeRules(tools_policy="visitor", tool_keys=["web_search"])
    unknown = SelectionModeRules(tools_policy="forced", tool_keys=["nope", "datagouv"])

    assert viability(forced, llms, tools=tools).viable is False
    assert viability(forced, llms, tools=tools).warnings == ["tool_not_offered"]
    assert viability(visitor, llms, tools=tools).viable is True
    assert viability(unknown, llms, tools=tools).viable is True
    assert set(viability(unknown, llms, tools=tools).warnings) == {
        "unknown_tool_keys",
        "tool_not_offered",
    }


# Tools


@pytest.mark.parametrize(
    "mode, requested, kept, shown",
    [
        (SelectionModeRules(tools_policy="none"), ["web_search"], [], []),
        (
            SelectionModeRules(tools_policy="forced", tool_keys=["web_search", "gone"]),
            [],
            ["web_search"],
            ["web_search"],
        ),
        (
            SelectionModeRules(tools_policy="forced", tool_keys=["web_search"]),
            ["datagouv"],
            ["web_search"],
            ["web_search"],
        ),
        (
            SelectionModeRules(tools_policy="visitor"),
            ["web_search", "web_search", "rogue"],
            ["web_search"],
            ["web_search", "datagouv"],
        ),
        (
            SelectionModeRules(tools_policy="visitor", tool_keys=["datagouv"]),
            ["web_search", "datagouv"],
            ["datagouv"],
            ["datagouv"],
        ),
    ],
)
def test_the_tools_policy_decides_the_tools(mode, requested, kept, shown):
    offered = ["web_search", "datagouv"]
    assert enabled_tools(mode, requested, offered) == kept
    assert allowed_tools(mode, offered) == shown


def test_a_pool_can_hold_systems_with_their_own_tools_or_the_others():
    system = llm("system", arena_tools=False)
    llms = [system, SMALL, BIG]

    assert filter_pool(llms, ModelFilter(arena_tools=False)) == [system.id]
    assert set(filter_pool(llms, ModelFilter(arena_tools=True))) == ids("small", "big")
    assert len(filter_pool(llms, ModelFilter())) == 3


def test_a_specialised_system_faces_a_generalist():
    system = llm("system", arena_tools=False, tags=["specialised"])
    llms = catalogue(system, SMALL, BIG)
    mode = SelectionModeRules(
        pool_a=ModelFilter(arena_tools=False, tags=["specialised"]),
        pool_b=ModelFilter(arena_tools=True),
        tools_policy="forced",
        tool_keys=["web_search"],
    )
    for pair in draws(mode, llms):
        assert system.id in pair
    assert viability(mode, llms).pairs == 2


def test_today_is_read_in_utc(monkeypatch):
    import backend.llms.selection as selection

    # 23:30 UTC on the 12th: already the 13th east of Greenwich, still the 12th
    # in UTC, which is the day mode windows are read in.
    monkeypatch.setattr(selection, "utc_now", lambda: datetime(2026, 11, 12, 23, 30))
    released = llm("released", release_date=date(2026, 11, 2))
    assert filter_pool([released], ModelFilter(released_within_days=10)) == [
        released.id
    ]
    monkeypatch.setattr(selection, "utc_now", lambda: datetime(2026, 11, 13, 0, 30))
    assert filter_pool([released], ModelFilter(released_within_days=10)) == []
