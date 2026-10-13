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


def replacements(
    llm_id_a: str, llm_id_b: str, expensive_available: bool
) -> set[str | None]:
    comparison: Any = SimpleNamespace(
        mode="random", llm_id_a=llm_id_a, llm_id_b=llm_id_b
    )

    async def draw() -> set[str | None]:
        return {
            await pick_replacement_model(comparison, "a", expensive_available)
            for _ in range(DRAWS)
        }

    return asyncio.run(draw())


def test_a_cheap_side_gets_a_cheap_stand_in() -> None:
    assert replacements("cheap-a", "expensive-a", expensive_available=True) <= set(
        CHEAP
    )


def test_an_expensive_side_may_get_an_expensive_stand_in() -> None:
    assert replacements("expensive-a", "cheap-a", expensive_available=True) & {
        "expensive-b"
    }


def test_an_expensive_side_gets_a_cheap_stand_in_once_the_allowance_is_spent() -> None:
    assert replacements("expensive-a", "cheap-a", expensive_available=False) <= set(
        CHEAP
    )
