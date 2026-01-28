import logging
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    RootModel,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

from backend.llms.models import PreferencesData
from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import FRONTEND_DIR, ROOT_DIR

from .llms import LLMDataRaw, LLMDataRawBase

logger = configure_logger(logging.getLogger("llms:organisations"))

LLMS_RAW_DATA_FILE = Path(__file__).parent / "models.json"

EXCLUDED_LLMS_STATUS = {"missing_data"}


# Model to validate organisations data from 'utils/models/models.json'
class RawOrganisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[LLMDataRawBase] | list[LLMDataRaw]

    @field_validator("icon_path", mode="after")
    @classmethod
    def check_icon_exists(cls, value: str) -> str:
        file_path = FRONTEND_DIR / "static" / "orgs" / "ai" / value
        if "." in value and not file_path.exists():
            raise PydanticCustomError(
                "file_missing",
                f"'icon_path' is defined but the file '{file_path.relative_to(ROOT_DIR)}' doesn't exists.",
            )

        return value

    @field_validator("models", mode="before")
    @classmethod
    def filter_excluded_llms_status(cls, models: list[Any]) -> list[Any]:
        filtered_llms: list[Any] = []

        for model in models:
            # Filter out some models based on attr `status`
            if model.get("status", None) in EXCLUDED_LLMS_STATUS:
                logger.warning(
                    f"LLM '{model["simple_name"]}' is excluded (reason={model["status"]})"
                )
                continue

            filtered_llms.append(model)

        return filtered_llms


# Model used to generated 'utils/models/generated-models.json'
class Organisation(RawOrganisation):
    models: list[LLMDataRaw]

    @field_validator("models", mode="before")
    @classmethod
    def enhance_models(cls, value: Any, info: ValidationInfo) -> list[LLMDataRawBase]:
        assert info.context is not None
        assert info.context["data"] is not None
        assert info.context["licenses"] is not None

        for model in value:
            # forward organisation data
            model["organisation"] = info.data.get("name")
            model["icon_path"] = info.data.get("icon_path")

            # forward/inject license data
            if model["license"] not in info.context["licenses"]:
                raise PydanticCustomError(
                    "license_missing",
                    f"license is defined but license data is missing in 'licenses.json' for license '{model["license"]}'",
                )

            for k, v in info.context["licenses"][model["license"]].items():
                model[k] = v

            if model["license"] == "proprietary":
                model["reuse"] = info.data["proprietary_reuse"]
                model["commercial_use"] = info.data["proprietary_commercial_use"]

            # inject ranking/prefs data
            data = info.context["data"].get(model["id"])

            if data:
                model["data"] = data

                PREFS_KEYS = list(PreferencesData.model_fields.keys())
                prefs = {key: data.pop(key) for key in PREFS_KEYS}
                if prefs:
                    model["prefs"] = prefs

        return value


RawOrgas = RootModel[list[RawOrganisation]]
Orgas = RootModel[list[Organisation]]


def validate_orgas_and_models(raw_orgas: Any, context: dict[str, Any]) -> list[Any]:
    try:
        orgas = RawOrgas.model_validate(raw_orgas, context=context).model_dump()
        logger.info("No errors in 'models.json'!")
        return orgas
    except ValidationError as exc:
        errors: dict[str, list[dict[str, Any]]] = {}

        for err in exc.errors():
            orga = raw_orgas[err["loc"][0]]
            if len(err["loc"]) <= 2:
                name = f"organisation '{orga.get("name", err["loc"][0])}'"
                key = err["loc"][1]
            elif "models" in err["loc"]:
                name = f"model '{orga["models"][err["loc"][2]]["id"]}'"
                key = err["type"] if err["type"] == "endpoint" else err["loc"][3]

            if name not in errors:
                errors[name] = []
            errors[name].append({"key": key, **err})

        log_pydantic_parsed_errors(logger, errors)

        raise Exception("Errors in 'models.json', exiting...")
