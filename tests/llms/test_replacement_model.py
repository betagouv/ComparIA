"""
Which model may take over from one that timed out.

The character budgets are charged before the models answer, at the pricey
rate only when one of the two models is pricey. A first-turn timeout swaps a
model mid-turn, after that charge, so a cheap pair must not be handed a
pricey model: the turn would get it without paying the pricey budget.
"""

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid5

import pytest

from backend.llms.data import LLMsData
from backend.llms.models import LLMDataEnabled
from backend.selection_modes import services as modes_services
from backend.selection_modes.services import pick_replacement_model

NAMESPACE = UUID("8a1d2b3c-4e5f-4a6b-9c8d-7e6f5a4b3c2d")
CHEAP = {name: uuid5(NAMESPACE, name) for name in ["cheap-a", "cheap-b", "cheap-c"]}
PRICEY = {name: uuid5(NAMESPACE, name) for name in ["pricey-a", "pricey-b"]}
IDS = CHEAP | PRICEY
# Enough draws that a pricey model would show up if it could: each draw has
# at least a one in three chance of one.
DRAWS = 50


@pytest.fixture(autouse=True)
def catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    models = [
        LLMDataEnabled.model_construct(
            id=llm_id, status="enabled", params=10, rate_limited=name in PRICEY
        )
        for name, llm_id in IDS.items()
    ]
    llms = LLMsData.model_construct(all={model.id: model for model in models})

    async def get_llms_data() -> Any:
        return llms

    async def find_selection_mode(_key: str) -> None:
        # The comparison's mode was deleted since: the whole catalogue.
        return None

    monkeypatch.setattr(modes_services, "get_llms_data", get_llms_data)
    monkeypatch.setattr(modes_services, "find_selection_mode", find_selection_mode)


def replacements(llm_a: str, llm_b: str, charged: bool) -> set[str | None]:
    names = {llm_id: name for name, llm_id in IDS.items()}
    comparison: Any = SimpleNamespace(
        mode="random", llm_id_a=IDS[llm_a], llm_id_b=IDS[llm_b]
    )

    async def draw() -> set[str | None]:
        picked = [
            await pick_replacement_model(comparison, "a", charged=charged)
            for _ in range(DRAWS)
        ]
        return {names.get(llm_id) if llm_id else None for llm_id in picked}

    return asyncio.run(draw())


def test_a_cheap_pair_already_charged_gets_no_pricey_model() -> None:
    assert replacements("cheap-a", "cheap-b", charged=True) == {"cheap-c"}


def test_a_pair_charged_at_the_pricey_rate_may_get_a_pricey_model() -> None:
    assert replacements("cheap-a", "pricey-a", charged=True) & set(PRICEY)


def test_a_swap_charged_afterwards_keeps_the_whole_pool() -> None:
    # `/retry` swaps before it charges, so the charge sees the new model.
    assert replacements("cheap-a", "cheap-b", charged=False) & set(PRICEY)


def test_a_failing_model_is_replaced_from_its_own_pool_whatever_its_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.arena.modes import SEEDED

    sizes = {"small-1": 8, "small-2": 20, "big-1": 500, "big-2": 700}
    ids = {name: uuid5(NAMESPACE, name) for name in sizes}
    models = [
        LLMDataEnabled.model_construct(
            id=ids[name], status="enabled", params=params, rate_limited=False
        )
        for name, params in sizes.items()
    ]
    llms = LLMsData.model_construct(all={model.id: model for model in models})
    looked_up: list[str] = []

    async def get_llms_data() -> Any:
        return llms

    async def find_selection_mode(key: str) -> Any:
        looked_up.append(key)
        return SEEDED[key]

    monkeypatch.setattr(modes_services, "get_llms_data", get_llms_data)
    monkeypatch.setattr(modes_services, "find_selection_mode", find_selection_mode)
    names = {llm_id: name for name, llm_id in ids.items()}
    # The draw swapped sides: pool B's small model sits on side a.
    comparison: Any = SimpleNamespace(
        mode="big-vs-small", llm_id_a=ids["small-1"], llm_id_b=ids["big-1"]
    )

    async def draw() -> set[str]:
        return {
            names[await pick_replacement_model(comparison, "a")] for _ in range(DRAWS)
        }

    assert asyncio.run(draw()) == {"small-2"}
    assert set(looked_up) == {"big-vs-small"}
