from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from utils.database.models.llms.llm import LLMDataUpsert
from utils.utils import FormJsonSchema


def payload(**overrides):
    return {
        "status": "enabled",
        "name": "Test LLM",
        "human_id": "test-llm",
        "api_model_id": "test-llm",
        "endpoint_id": uuid4(),
        "cost_weight": 1.0,
        "lab_id": uuid4(),
        "release_date": date(2026, 1, 1),
        "license_id": uuid4(),
        "public_weights": True,
        "public_training_data": False,
        "public_training_code": False,
        "eu_hostable": True,
        "arch": "dense",
        "params": 7.0,
        "inputs": ["text"],
        "price_in": 1.0,
        "price_out": 2.0,
        **overrides,
    }


def test_fields_the_form_shows_as_optional_are_not_required_by_the_api():
    """
    The admin form only sends the fields the user touched, so a field it draws
    as optional must have a default, or creating an LLM fails with 422.
    """
    schema = LLMDataUpsert.model_json_schema(schema_generator=FormJsonSchema)
    optional = {k for k, v in schema["properties"].items() if v.get("optional")}

    assert optional
    assert optional & set(schema["required"]) == set()


def test_an_llm_can_be_created_without_the_optional_fields():
    llm = LLMDataUpsert(
        **{
            k: v
            for k, v in payload().items()
            if k not in ("api_model_id", "endpoint_id")
        }
    )

    assert llm.system_prompt is None
    assert llm.active_params is None
    assert llm.context_tokens is None
    assert llm.quantization is None


def test_a_moe_llm_still_needs_active_params():
    with pytest.raises(ValidationError, match="active_params"):
        LLMDataUpsert(**payload(arch="moe"))

    assert LLMDataUpsert(**payload(arch="moe", active_params=1.0)).active_params == 1.0


def test_an_llm_without_an_endpoint_is_disabled():
    llm = LLMDataUpsert(**payload(status="enabled", endpoint_id=None))

    assert llm.status == "disabled"


def test_links_are_not_required_in_the_admin_form():
    """
    An LLM card without links is fine, and the list starts empty, so the form
    should not mark the fieldset with a required asterisk.
    """
    schema = LLMDataUpsert.model_json_schema(schema_generator=FormJsonSchema)

    assert schema["properties"]["links"]["optional"] is True
    assert "links" not in schema["required"]


def test_llm_metadata_dates_are_date_only():
    llm = LLMDataUpsert(
        **payload(release_date="2026-01-02", knowledge_cutoff="2025-12-31")
    )

    assert llm.release_date == date(2026, 1, 2)
    assert llm.knowledge_cutoff == date(2025, 12, 31)
    assert llm.model_dump(mode="json")["release_date"] == "2026-01-02"

    with pytest.raises(ValidationError):
        LLMDataUpsert(**payload(release_date="2026-01-02T12:30:00"))


def test_an_llm_left_without_a_cost_weight_costs_as_much_as_an_ordinary_one():
    llm = LLMDataUpsert(**{k: v for k, v in payload().items() if k != "cost_weight"})

    assert llm.cost_weight == 1.0


def test_a_cost_weight_below_one_is_refused():
    with pytest.raises(ValidationError, match="cost_weight"):
        LLMDataUpsert(**payload(cost_weight=0.5))

    assert LLMDataUpsert(**payload(cost_weight=4)).cost_weight == 4.0


def test_a_cost_weight_the_form_cleared_is_an_ordinary_one():
    assert LLMDataUpsert(**payload(cost_weight=None)).cost_weight == 1.0


@pytest.mark.parametrize("weight", [2.5, 100])
def test_a_cost_weight_up_to_a_hundred_is_kept(weight):
    assert LLMDataUpsert(**payload(cost_weight=weight)).cost_weight == weight


@pytest.mark.parametrize("weight", [100.5, float("inf"), float("nan")])
def test_a_cost_weight_above_a_hundred_or_not_finite_is_refused(weight):
    with pytest.raises(ValidationError, match="cost_weight"):
        LLMDataUpsert(**payload(cost_weight=weight))
