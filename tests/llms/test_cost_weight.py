from uuid import uuid4

from backend.llms.data import LLMsData
from backend.llms.models import LLMDataArchived, LLMDataEnabled

ORDINARY, EXPENSIVE, A_LITTLE, ARCHIVED = uuid4(), uuid4(), uuid4(), uuid4()


def llms_data() -> LLMsData:
    return LLMsData.model_construct(
        all={
            ORDINARY: LLMDataEnabled.model_construct(
                id=ORDINARY, status="enabled", cost_weight=1.0
            ),
            EXPENSIVE: LLMDataEnabled.model_construct(
                id=EXPENSIVE, status="enabled", cost_weight=4.0
            ),
            A_LITTLE: LLMDataEnabled.model_construct(
                id=A_LITTLE, status="enabled", cost_weight=2.5
            ),
            ARCHIVED: LLMDataArchived.model_construct(
                id=ARCHIVED, status="archived", cost_weight=4.0
            ),
        }
    )


def test_only_enabled_models_above_weight_one_are_expensive():
    assert llms_data().expensive_models == [EXPENSIVE, A_LITTLE]


def test_weight_reads_the_cost_weight_of_any_known_model():
    data = llms_data()

    assert data.weight(ORDINARY) == 1.0
    assert data.weight(EXPENSIVE) == 4.0
    assert data.weight(A_LITTLE) == 2.5
    assert data.weight(ARCHIVED) == 4.0
