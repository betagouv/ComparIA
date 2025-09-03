import json
import rich
import logging
import markdown
from pathlib import Path
from pydantic import BaseModel, RootModel, ValidationError
from rich import print
from rich.logging import RichHandler
from slugify import slugify
from typing import Any, Literal, Tuple, get_args, Annotated
from utils import Obj, read_json, write_json, filter_dict, sort_dict


logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="|", handlers=[RichHandler()]
)
log = logging.getLogger("models")

CURRENT_FOLDER = Path(__file__).parent
LICENSES_PATH = CURRENT_FOLDER / "licenses.json"
MODELS_PATH = CURRENT_FOLDER / "models.json"
MODELS_EXTRA_DATA_PATH = CURRENT_FOLDER / "generated-models-extra-data.json"
GENERATED_MODELS_PATH = CURRENT_FOLDER / "generated-models.json"
I18N_PATH = (
    CURRENT_FOLDER.parent.parent / "frontend" / "locales" / "messages" / "fr.json"
)

I18N_OS_LICENSE_KEYS = [
    "license_desc",
    "reuse_specificities",
    "commercial_use_specificities",
]
I18N_PROPRIO_LICENSE_KEYS = ["proprietary_" + k for k in I18N_OS_LICENSE_KEYS]
I18N_MODEL_KEYS = ["desc", "size_desc", "fyi"]

PARAMS_SIZE_MAP = {"XS": 3, "S": 7, "M": 35, "L": 70, "XL": 200}


class License(BaseModel):
    license: str
    license_desc: str
    distribution: Literal["api-only", "open-weights", "fully-open-source"]
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


class Endpoint(BaseModel):
    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str

class Model(BaseModel):
    status: Literal["archived", "missing_data", "disabled", "enabled"] | None = (
        "enabled"
    )
    id: str | None = None  # FIXME required?
    simple_name: str
    license: str
    fully_open_source: bool | None = None
    release_date: str
    params: int | float | Literal["XS", "S", "M", "L", "XL"]
    active_params: int | float | None = None
    arch: str
    reasoning: bool | Literal["hybrid"] = False
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None  # FIXME required?
    desc: str
    size_desc: str
    fyi: str
    endpoint: Endpoint


class Organisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[Model]


Licenses = RootModel[list[License]]
Orgas = RootModel[list[Organisation]]


def log_errors(errors: dict[str, list[Obj]]) -> None:
    for name, errs in errors.items():
        log.error(
            f"Error in {name}:\n"
            + "\n".join(
                [
                    f"- {err['key']}: [type={err['type']}] {err['msg']} (input={err['input'] if err['type'] != 'missing' else None})"
                    for err in errs
                ]
            )
        )


def validate_licenses(raw_licenses: Any) -> list[Any] | None:
    try:
        return Licenses(raw_licenses).model_dump(exclude_none=True)
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

        for err in exc.errors():
            name = f"license '{raw_licenses[err["loc"][0]]["license"]}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": err["loc"][1], **err})

        log_errors(errors)
        return None


def validate_orgas_and_models(raw_orgas: Any) -> list[Any] | None:
    try:
        return Orgas(raw_orgas).model_dump(exclude_none=True)
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

        for err in exc.errors():
            orga = raw_orgas[err["loc"][0]]
            if len(err["loc"]) <= 2:
                name = f"organisation '{orga.get("name", err["loc"][0])}'"
                key = err["loc"][1]
            elif "models" in err["loc"]:
                name = f"model '{orga["models"][err["loc"][2]]["simple_name"]}'"
                key = err["loc"][3]

            if name not in errors:
                errors[name] = []
            errors[name].append({"key": key, **err})

        log_errors(errors)

        return None


def params_to_friendly_size(params):
    """
    Converts a parameter value to a friendly size description.

    Args:
        param (int): The parameter value

    Returns:
        str: The friendly size description
    """
    intervals = [(0, 7), (7, 20), (20, 70), (70, 150), (150, float("inf"))]
    sizes = ["XS", "S", "M", "L", "XL"]

    for i, (lower, upper) in enumerate(intervals):
        if lower <= params < upper:
            return sizes[i]

    raise Exception("Error: Could not guess friendly_size")


def validate() -> None:
    raw_licenses = read_json(LICENSES_PATH)
    raw_orgas = read_json(MODELS_PATH)
    raw_extra_data = read_json(MODELS_EXTRA_DATA_PATH)

    # Filter out some models based on attr `status`
    for orga in raw_orgas:
        filtered_models = []
        for model in orga["models"]:
            if model.get("status", None) == "missing_data":
                log.warning(
                    f"Model '{model["simple_name"]}' is deactivated (reason={model["status"]})"
                )
            else:
                filtered_models.append(model)
        orga["models"] = filtered_models

    dumped_licenses = validate_licenses(raw_licenses)
    dumped_orgas = validate_orgas_and_models(raw_orgas)

    if not dumped_licenses or not dumped_orgas:
        return

    dict_licenses = {license["license"]: license for license in dumped_licenses}
    base_proprietary_license = dict_licenses.pop("proprietary")

    i18n = {
        "licenses": {
            "os": sort_dict(
                {
                    license["license"]: {
                        k: (
                            (license[k] if k in license else "")
                            if k != "license_desc"
                            else markdown.markdown(license[k])
                        )
                        for k in I18N_OS_LICENSE_KEYS
                    }
                    for license in dict_licenses.values()
                }
            ),
            "proprio": {},
        },
        "models": {},
    }
    generated_models = {}

    for orga in dumped_orgas:
        i18n["licenses"]["proprio"][orga["name"]] = {
            k.replace("proprietary_", ""): orga[k] if k in orga else ""
            for k in I18N_PROPRIO_LICENSE_KEYS
        }
        proprio_license_data = {**base_proprietary_license}
        proprio_license_data["reuse"] = orga["proprietary_reuse"]
        proprio_license_data["commercial_use"] = orga.get(
            "proprietary_commercial_use", None
        )

        for model in orga["models"]:
            i18n["models"][model["simple_name"]] = {
                k: markdown.markdown(model[k]) for k in I18N_MODEL_KEYS
            }
            try:
                license_data = (
                    dict_licenses[model["license"]]
                    if model["license"] != "proprietary"
                    else proprio_license_data
                )
            except KeyError as e:
                log.error(
                    f"Incorrect or missing license data in 'licenses.json' for license '{model["license"]}'"
                )
                return

            # Enhance model data
            model_data = filter_dict(model, I18N_MODEL_KEYS)

            if model_data.get("fully_open_source"):
                model_data["distribution"] = "fully_open_source"

            if isinstance(model_data["params"], str):
                model_data["friendly_size"] = model_data["params"]
                # Guess params
                model_data["params"] = PARAMS_SIZE_MAP[model_data["params"]]
            else:
                model_data["friendly_size"] = params_to_friendly_size(
                    model_data["params"]
                )

            if model.get("quantization", None) == "q8":
                model_data["required_ram"] = model_data["params"] * 2
            else:
                # We suppose from q4 to fp16
                model_data["required_ram"] = model_data["params"]

            # FIXME to remove, should be required
            model_id = model["id"] if "id" in model else slugify(model["simple_name"])

            model_extra_data = next(
                (
                    m
                    for m in raw_extra_data
                    if m["model_name"] == model_id or m["name"] == model["simple_name"]
                ),
                None,
            )
            if model_extra_data is not None:
                model_extra_data = {
                    "elo": round(model_extra_data["median"]),
                    "trust_range": [
                        round(model_extra_data["median_minus_p2.5"]),
                        round(model_extra_data["p97.5_minus_median"]),
                    ],
                    "total_votes": model_extra_data["n_match"],
                    "consumption_wh": round(
                        model_extra_data["mean_wh_per_thousand_token"]
                    ),
                }

            # Build complete model data (license + model) without translatable keys
            generated_models[model_id] = sort_dict(
                {
                    "organisation": orga["name"],
                    "icon_path": orga["icon_path"],
                    **filter_dict(license_data, I18N_OS_LICENSE_KEYS),
                    **model_data,
                    **(model_extra_data or {}),
                    "id": model_id,
                }
            )

    i18n["licenses"]["proprio"] = sort_dict(i18n["licenses"]["proprio"])
    i18n["models"] = sort_dict(i18n["models"])

    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(I18N_PATH)
    frontend_i18n["generated"] = sort_dict(i18n)

    write_json(I18N_PATH, frontend_i18n, indent=4)
    write_json(GENERATED_MODELS_PATH, sort_dict(generated_models))


if __name__ == "__main__":
    validate()
