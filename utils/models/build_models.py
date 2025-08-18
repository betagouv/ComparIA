import json
import rich
import logging
from pathlib import Path
from pydantic import BaseModel, RootModel, ValidationError
from rich import print
from rich.logging import RichHandler
from slugify import slugify
from typing import Any, Literal, Tuple, get_args, Annotated

Obj = dict[str, Any]

logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="|", handlers=[RichHandler()]
)
log = logging.getLogger("models")

CURRENT_FOLDER = Path(__file__).parent
LICENSES_PATH = CURRENT_FOLDER / "licenses.json"
MODELS_PATH = CURRENT_FOLDER / "models.json"
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


class License(BaseModel):
    license: str
    license_desc: str
    distribution: Literal["api-only", "open-weights", "fully-open-source"]
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


class Model(BaseModel):
    name: str
    license: str
    release_date: str
    params: int | float | Literal["XS", "S", "M", "L", "XL"]
    arch: str
    desc: str
    size_desc: str
    fyi: str


class Organisation(BaseModel):
    name: str
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[Model]


Licenses = RootModel[list[License]]
Orgas = RootModel[list[Organisation]]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def filter_dict(data: Obj, exclude: list[str]) -> Obj:
    return {k: data[k] for k in set(data.keys()).difference(exclude)}


def sort_dict(data: Obj) -> Obj:
    return dict(sorted(data.items()))


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
        return Licenses(raw_licenses).model_dump()
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
        return Orgas(raw_orgas).model_dump()
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

        for err in exc.errors():
            orga = raw_orgas[err["loc"][0]]
            if len(err["loc"]) <= 2:
                name = f"organisation '{orga.get("name", err["loc"][0])}'"
                key = err["loc"][1]
            elif "models" in err["loc"]:
                name = f"model '{orga["models"][err["loc"][2]]["name"]}'"
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
                        k: license[k] or "" for k in I18N_OS_LICENSE_KEYS
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
            k.replace("proprietary_", ""): orga[k] or ""
            for k in I18N_PROPRIO_LICENSE_KEYS
        }
        proprio_license_data = {**base_proprietary_license}
        proprio_license_data["reuse"] = orga["proprietary_reuse"]
        proprio_license_data["commercial_use"] = orga["proprietary_commercial_use"]

        for model in orga["models"]:
            i18n["models"][model["name"]] = {k: model[k] for k in I18N_MODEL_KEYS}
            license_data = (
                dict_licenses[model["license"]]
                if model["license"] != "proprietary"
                else proprio_license_data
            )

            # Enhance model data
            model_data = filter_dict(model, I18N_MODEL_KEYS)

            if isinstance(model_data["params"], str):
                model_data["friendly_size"] = model_data["params"]
                model_data["params"] = None
            else:
                model_data["friendly_size"] = params_to_friendly_size(
                    model_data["params"]
                )

            # Build complete model data (license + model) without translatable keys
            generated_models[slugify(model["name"])] = sort_dict(
                {
                    "organisation": orga["name"],
                    **filter_dict(license_data, I18N_OS_LICENSE_KEYS),
                    **model_data,
                }
            )

    i18n["licenses"]["proprio"] = sort_dict(i18n["licenses"]["proprio"])
    i18n["models"] = sort_dict(i18n["models"])

    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(I18N_PATH)
    frontend_i18n["generated"] = sort_dict(i18n)

    write_json(I18N_PATH, frontend_i18n)
    write_json(GENERATED_MODELS_PATH, sort_dict(generated_models))


if __name__ == "__main__":
    validate()
