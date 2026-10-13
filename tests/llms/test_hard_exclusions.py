"""
Models a draw must never hand out, such as expensive ones once the person's
allowance for them is spent.

`pick_one` used to put excluded models back when nothing else was left. That
is right for a preference, and wrong for a model the person may not use.
"""

from uuid import uuid4

import pytest

from backend.llms.data import LLMsData, NoModelLeft
from backend.llms.models import LLMDataEnabled

SMALL = [uuid4(), uuid4()]
BIG_CHEAP = uuid4()
EXPENSIVE = [uuid4(), uuid4()]
# Enough draws that an excluded model would show up if it could.
DRAWS = 50


def llms_data(big=(BIG_CHEAP, *EXPENSIVE)) -> LLMsData:
    def llm(llm_id, params):
        return LLMDataEnabled.model_construct(
            id=llm_id,
            status="enabled",
            params=params,
            cost_weight=4.0 if llm_id in EXPENSIVE else 1.0,
        )

    return LLMsData.model_construct(
        all={
            **{llm_id: llm(llm_id, 7) for llm_id in SMALL},
            **{llm_id: llm(llm_id, 400) for llm_id in big},
        }
    )


def drawn(mode, selection=None, data=None) -> set:
    data = data or llms_data()
    return {
        llm_id
        for _ in range(DRAWS)
        for llm_id in data.pick_two(
            mode, selection, hard_excluded=data.expensive_models
        )
    }


def test_pick_one_never_puts_a_hard_exclusion_back():
    data = llms_data()
    only = SMALL[0]
    picks = {
        data.pick_one([only, *EXPENSIVE], excluded=[only], hard_excluded=EXPENSIVE)
        for _ in range(DRAWS)
    }
    assert picks == {only}


def test_pick_one_with_nothing_left_raises():
    with pytest.raises(NoModelLeft) as refusal:
        llms_data().pick_one(EXPENSIVE, hard_excluded=EXPENSIVE)
    assert refusal.value.llm_ids == []


@pytest.mark.parametrize("mode", ["random", "big-vs-small", "small-models"])
def test_no_mode_draws_an_excluded_model(mode):
    assert not drawn(mode) & set(EXPENSIVE)


def test_a_mode_with_every_big_model_excluded_has_nothing_to_draw():
    with pytest.raises(NoModelLeft):
        drawn("big-vs-small", data=llms_data(big=EXPENSIVE))


def test_a_custom_pick_of_an_excluded_model_is_refused_with_its_id():
    with pytest.raises(NoModelLeft) as refusal:
        drawn("custom", [str(SMALL[0]), str(EXPENSIVE[1])])
    assert refusal.value.llm_ids == [EXPENSIVE[1]]


def test_the_partner_of_a_single_pick_is_drawn_from_the_allowed_models():
    picked = SMALL[0]
    assert drawn("custom", [str(picked)]) <= {*SMALL, BIG_CHEAP}
