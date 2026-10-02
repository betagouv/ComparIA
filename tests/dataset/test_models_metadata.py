import asyncio
import json
from datetime import date, datetime
from uuid import uuid4

from backend.llms.models import APILLMDataBase
from utils.dataset import compute

NOW = datetime(2026, 1, 1)


def llm(
    human_id: str, status: str = "enabled", license_kind: str = "open-source"
) -> APILLMDataBase:
    return APILLMDataBase.model_validate(
        {
            "id": uuid4(),
            "created_at": NOW,
            "updated_at": NOW,
            "status": status,
            "name": human_id.title(),
            "human_id": human_id,
            "api_model_id": f"provider/{human_id}",
            "endpoint_id": uuid4(),
            "rate_limited": True,
            "lab_id": uuid4(),
            "lab": {
                "id": uuid4(),
                "created_at": NOW,
                "updated_at": NOW,
                "name": "Lab",
                "logo": "lab",
                "origin_country": "FR",
            },
            "release_date": date(2026, 1, 1),
            "license_id": uuid4(),
            "license": {
                "id": uuid4(),
                "created_at": NOW,
                "updated_at": NOW,
                "kind": license_kind,
                "name": "Apache 2.0",
                "reuse": True,
                "commercial_use": True,
            },
            "public_weights": True,
            "public_training_data": False,
            "public_training_code": False,
            "eu_hostable": True,
            "arch": "dense",
            "params": 7.0,
            "inputs": ["text"],
            "price_in": 1.0,
            "price_out": 2.0,
        }
    )


def write(tmp_path, llms: list[APILLMDataBase]) -> list[dict]:
    async def _llms_data():
        return {m.id: m for m in llms}

    compute.get_llms_data, original = _llms_data, compute.get_llms_data
    try:
        asyncio.run(compute.write_models_metadata(tmp_path))
    finally:
        compute.get_llms_data = original
    return json.loads((tmp_path / compute.MODELS_FILENAME).read_text())


def test_models_are_listed_by_human_id_with_their_uuid(tmp_path):
    b, a = llm("model-b", status="archived"), llm("model-a")

    models = write(tmp_path, [b, a])

    assert [m["human_id"] for m in models] == ["model-a", "model-b"]
    assert models[0]["id"] == str(a.id)
    assert models[1]["status"] == "archived"


def test_models_carry_metadata_but_no_internal_plumbing(tmp_path):
    (model,) = write(tmp_path, [llm("model-a")])

    assert model["params"] == 7.0
    assert model["release_date"] == "2026-01-01"
    assert model["lab"] == {"name": "Lab", "origin_country": "FR"}
    assert model["license"]["name"] == "Apache 2.0"
    assert model["size_class"] == "XS"
    assert model["energy_class"] is not None
    for key in (
        "wh_per_million_token",
        "api_model_id",
        "endpoint_id",
        "rate_limited",
        "lab_id",
        "license_id",
        "created_at",
        "updated_at",
    ):
        assert key not in model
    assert "id" not in model["license"]


def test_proprietary_models_hide_their_estimated_size(tmp_path):
    (model,) = write(tmp_path, [llm("model-a", license_kind="proprietary")])

    for key in ("params", "active_params", "size_class", "required_ram"):
        assert model[key] is None, key
    assert model["energy_class"] is not None
    assert model["arch"] == "dense"
