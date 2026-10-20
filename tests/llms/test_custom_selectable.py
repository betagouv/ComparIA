"""
Which models a visitor may pick themselves in custom mode.

An admin can lock an LLM out of custom mode, so nobody can pin it on every
comparison. It still comes up in random draws.
"""

from uuid import UUID, uuid4

import pytest

from backend.llms.data import LLMsData
from backend.llms.models import LLMDataEnabled

OPEN = uuid4()
OTHER = uuid4()
LOCKED = uuid4()
DRAWS = 50


@pytest.fixture
def llms() -> LLMsData:
    def llm(id: UUID, custom_selectable: bool) -> LLMDataEnabled:
        return LLMDataEnabled.model_construct(
            id=id, status="enabled", params=10, custom_selectable=custom_selectable
        )

    models = [llm(OPEN, True), llm(OTHER, True), llm(LOCKED, False)]
    return LLMsData.model_construct(all={model.id: model for model in models})


def test_an_open_pair_goes_through(llms: LLMsData) -> None:
    assert set(llms.pick_two("custom", (str(OPEN), str(OTHER)))) == {OPEN, OTHER}


@pytest.mark.parametrize(
    "selection", [(str(LOCKED),), (str(OPEN), str(LOCKED)), (str(LOCKED), str(OPEN))]
)
def test_a_locked_model_is_refused(llms: LLMsData, selection: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="locked"):
        llms.pick_two("custom", selection)


def test_a_locked_model_still_comes_up_at_random(llms: LLMsData) -> None:
    drawn = {model for _ in range(DRAWS) for model in llms.pick_two("random")}
    assert LOCKED in drawn
