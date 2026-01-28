import logging
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from backend.llms.models import DatasetData, PreferencesData
from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import ROOT_DIR

logger = configure_logger(logging.getLogger("llms:dataset_data"))

LLMS_DATASET_DATA_FILE = Path(__file__).parent / "generated-models-extra-data.json"

RANKING_KEYS = [
    (
        field.validation_alias.choices[0]
        if field.validation_alias and hasattr(field.validation_alias, "choices")
        else k
    )
    for k, field in DatasetData.model_fields.items()
]
PREFS_KEYS = list(PreferencesData.model_fields.keys())


class RankingDataLLM(BaseModel):
    data: DatasetData | None
    prefs: PreferencesData | None

    @model_validator(mode="before")
    @classmethod
    def separate_data(cls, data: Any) -> Any:
        ranking = {key: data.get(key) for key in RANKING_KEYS if key in data}
        prefs = {key: data.get(key) for key in PREFS_KEYS if key in data}

        return {"data": ranking or None, "prefs": prefs or None}


class RankingData(BaseModel):
    timestamp: float
    models: dict[str, RankingDataLLM]

    @field_validator("models", mode="before")
    @classmethod
    def list_to_dict(cls, value: Any, info: ValidationInfo) -> dict[Any, Any]:
        return {m["model_name"]: m for m in value}


def get_dataset_data(raw_dataset_data: Any):
    try:
        dataset_data = RankingData.model_validate(raw_dataset_data)
        logger.info(f"No errors in '{LLMS_DATASET_DATA_FILE.relative_to(ROOT_DIR)}'!")
        return dataset_data
    except ValidationError as exc:
        errors: dict[str, list[dict[str, Any]]] = {}

        for err in exc.errors():
            if err["loc"][0] != "models" or len(err["loc"]) <= 1:
                name = f"dataset data"
                key = err["loc"][0]
            else:
                _, llm_id, data_type, data_key = err["loc"]
                name = f"value for '{llm_id}'"
                key = f"{data_type}.{data_key}"

            if name not in errors:
                errors[name] = []
            errors[name].append({"key": key, **err})

        log_pydantic_parsed_errors(logger, errors)

    raise Exception(
        f"Errors in '{LLMS_DATASET_DATA_FILE.relative_to(ROOT_DIR)}', exiting..."
    )
