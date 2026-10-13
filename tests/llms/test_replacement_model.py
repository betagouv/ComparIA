"""
Which model may take over from one that timed out.

The character budgets are charged before the models answer, at the expensive
rate only when one of the two models is expensive. A first-turn timeout swaps a
model mid-turn, after that charge, so a cheap pair must not be handed an
expensive model: the turn would get it without paying the expensive budget.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.llms import data
from backend.llms.data import LLMsData, pick_replacement_model

CHEAP = ["cheap-a", "cheap-b", "cheap-c"]
EXPENSIVE = ["expensive-a", "expensive-b"]
# Enough draws that an expensive model would show up if it could: each draw has
# at least a one in three chance of one.
DRAWS = 50


@pytest.fixture(autouse=True)
def catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_llms_data() -> Any:
        return SimpleNamespace(
            random_models=CHEAP + EXPENSIVE,
            expensive_models=EXPENSIVE,
            pick_one=lambda models, excluded: LLMsData.pick_one(
                cast(Any, None), models, excluded
            ),
        )

    monkeypatch.setattr(data, "get_llms_data", get_llms_data)


def replacements(llm_id_a: str, llm_id_b: str, charged: bool) -> set[str | None]:
    comparison: Any = SimpleNamespace(
        mode="random", llm_id_a=llm_id_a, llm_id_b=llm_id_b
    )

    async def draw() -> set[str | None]:
        return {
            await pick_replacement_model(comparison, "a", charged=charged)
            for _ in range(DRAWS)
        }

    return asyncio.run(draw())


def test_a_cheap_pair_already_charged_gets_no_expensive_model() -> None:
    assert replacements("cheap-a", "cheap-b", charged=True) == {"cheap-c"}


def test_a_pair_charged_at_the_expensive_rate_may_get_an_expensive_model() -> None:
    assert replacements("cheap-a", "expensive-a", charged=True) & set(EXPENSIVE)


def test_a_swap_charged_afterwards_keeps_the_whole_pool() -> None:
    # `/retry` swaps before it charges, so the charge sees the new model.
    assert replacements("cheap-a", "cheap-b", charged=False) & set(EXPENSIVE)
