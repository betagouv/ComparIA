"""
Which model may take over from one that failed.

Only an expensive model may stand in for an expensive one, and only while the
person's expensive allowance has room. A cheap side was charged at the cheap
rate, and a person with no expensive allowance left must not get an expensive
model through a stand-in.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

import backend.arena.limits as limits
from backend.llms import data
from backend.llms.data import LLMsData, pick_replacement_model

CHEAP = ["cheap-a", "cheap-b", "cheap-c"]
EXPENSIVE = ["expensive-a", "expensive-b"]
# Enough draws that an expensive model would show up if it could: each draw has
# at least a one in three chance of one.
DRAWS = 50


# Priced under and over the threshold.
MODELS = [
    SimpleNamespace(
        id=llm_id,
        price_in=2.6 if llm_id in EXPENSIVE else 0.2,
        price_out=13.0 if llm_id in EXPENSIVE else 1.0,
        daily_usd_cap=None,
    )
    for llm_id in CHEAP + EXPENSIVE
]


@pytest.fixture(autouse=True)
def catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_llms_data() -> Any:
        return SimpleNamespace(
            random_models=CHEAP + EXPENSIVE,
            pick_one=lambda models, excluded: LLMsData.pick_one(
                cast(Any, None), models, excluded
            ),
        )

    monkeypatch.setattr(data, "get_llms_data", get_llms_data)
    monkeypatch.setattr(limits, "_stored", {})


def replacements(
    llm_id_a: str, llm_id_b: str, expensive_paused: bool
) -> set[str | None]:
    comparison: Any = SimpleNamespace(
        mode="random", llm_id_a=llm_id_a, llm_id_b=llm_id_b
    )
    left_out = limits.stand_in_exclusions(MODELS, cast(Any, llm_id_a), expensive_paused)

    async def draw() -> set[str | None]:
        return {
            await pick_replacement_model(comparison, "a", left_out)
            for _ in range(DRAWS)
        }

    return asyncio.run(draw())


def test_a_cheap_side_gets_a_cheap_stand_in() -> None:
    assert replacements("cheap-a", "expensive-a", expensive_paused=False) <= set(CHEAP)


def test_an_expensive_side_may_get_an_expensive_stand_in() -> None:
    assert replacements("expensive-a", "cheap-a", expensive_paused=False) & {
        "expensive-b"
    }


def test_an_expensive_side_gets_a_cheap_stand_in_once_the_allowance_is_spent() -> None:
    assert replacements("expensive-a", "cheap-a", expensive_paused=True) <= set(CHEAP)


def test_a_model_full_for_the_day_never_stands_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limits, "full_models", lambda _llms: {"cheap-b": None})

    assert replacements("cheap-a", "expensive-a", expensive_paused=False) == {"cheap-c"}
