from uuid import uuid4

from backend.config import settings
from backend.llms.data import LLMsData
from backend.llms.models import LLMDataArchived, LLMDataEnabled

ORDINARY, EXPENSIVE, AT_THRESHOLD, FREE, ARCHIVED = (uuid4() for _ in range(5))


def llms_data() -> LLMsData:
    def enabled(llm_id, price_out):
        return LLMDataEnabled.model_construct(
            id=llm_id, status="enabled", price_in=price_out / 5, price_out=price_out
        )

    return LLMsData.model_construct(
        all={
            ORDINARY: enabled(ORDINARY, 1.3),
            EXPENSIVE: enabled(EXPENSIVE, 13.0),
            AT_THRESHOLD: enabled(AT_THRESHOLD, settings.RATELIMIT_EXPENSIVE_PRICE_OUT),
            FREE: enabled(FREE, 0.0),
            ARCHIVED: LLMDataArchived.model_construct(
                id=ARCHIVED, status="archived", price_in=2.6, price_out=13.0
            ),
        }
    )


def test_enabled_models_priced_at_or_above_the_threshold_are_expensive():
    assert llms_data().expensive_models == [EXPENSIVE, AT_THRESHOLD]


def test_a_new_threshold_applies_at_once(monkeypatch):
    data = llms_data()
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PRICE_OUT", 20.0)
    assert data.expensive_models == []


def test_a_model_priced_zero_is_never_expensive(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PRICE_OUT", 0.0)
    assert FREE not in llms_data().expensive_models
    assert ORDINARY in llms_data().expensive_models
