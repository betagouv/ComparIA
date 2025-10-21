import logging
import markdown
import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field, RootModel, ValidationError
from rich.logging import RichHandler
from slugify import slugify
from typing import Any

from languia.reveal import get_llm_impact, convert_range_to_value
from languia.models import Licenses, Orgas, RawOrgas
from utils.models.utils import Obj, read_json, write_json, filter_dict, sort_dict

logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="|", handlers=[RichHandler()]
)
log = logging.getLogger("models")

CURRENT_FOLDER = Path(__file__).parent
FRONTEND_FOLDER = CURRENT_FOLDER.parent.parent / "frontend"
LICENSES_PATH = CURRENT_FOLDER / "licenses.json"
MODELS_PATH = CURRENT_FOLDER / "models.json"
MODELS_EXTRA_DATA_PATH = CURRENT_FOLDER / "generated-models-extra-data.json"
MODELS_PREFERENCES_PATH = CURRENT_FOLDER / "generated-preferences.json"
GENERATED_MODELS_PATH = CURRENT_FOLDER / "generated-models.json"
I18N_PATH = FRONTEND_FOLDER / "locales" / "messages" / "fr.json"
TS_DATA_PATH = FRONTEND_FOLDER / "src" / "lib" / "generated.ts"

I18N_OS_LICENSE_KEYS = [
    "license_desc",
    "reuse_specificities",
    "commercial_use_specificities",
]
I18N_PROPRIO_LICENSE_KEYS = ["proprietary_" + k for k in I18N_OS_LICENSE_KEYS]
I18N_MODEL_KEYS = ["desc", "size_desc", "fyi"]


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


def validate_orgas_and_models(raw_orgas: Any) -> RawOrgas | None:
    try:
        return RawOrgas(raw_orgas).model_dump()
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

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

        log_errors(errors)

        return None


def connect_to_db(DATABASE_URI):

    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError

    if not DATABASE_URI:
        log.error(
            "Cannot connect to the database: no $DATABASE_URI configuration provided."
        )

    try:
        engine = create_engine(DATABASE_URI)
    except Exception as e:
        log.error(f"Failed to create database engine: {e}")
        return {}


def fetch_distinct_model_ids(engine, models_data):
    """Get distinct model IDs from the conversations table."""

    import polars as pl

    query = "SELECT DISTINCT model_a_name as model_id FROM conversations UNION SELECT DISTINCT model_b_name as model_id FROM conversations"
    try:
        with engine.connect() as conn:
            df = pl.read_database(query=query, connection=conn)
            # Filter out None values if any
            model_ids = df["model_id"].dropna().unique().tolist()

            if not model_ids:
                log.warning("No model IDs found in the database.")
                return {}

            missing_models = []
            for model_id in model_ids:
                if model_id not in models_data:
                    missing_models.append(
                        f"'{model_id}' not found in generated-models.json"
                    )

            if missing_models:
                log.warning("Pre-check found missing models in generated-models.json:")
                for model in missing_models:
                    log.warning(f"- {model}")
            return [model_id.lower() for model_id in model_ids]
    except Exception as e:
        log.error(f"Failed to fetch distinct model IDs: {e}")
        return []


def get_ecologits_rate(models_data: dict) -> dict:
    """Calculates wh_per_million_token for each model."""

    wh_per_million_token_map = {}
    for model_id in models_data:
        model_info = models_data[model_id]

        impact = get_llm_impact(model_info, model_id, 1_000_000, None)

        if impact and hasattr(impact, "energy") and hasattr(impact.energy, "value"):
            energy_kwh = convert_range_to_value(impact.energy.value)
            energy_wh = energy_kwh * 1000
            wh_per_million_token_map[model_id] = energy_wh
    return wh_per_million_token_map


def params_to_friendly_size(params):
    """
    Converts a parameter value to a friendly size description.

    Args:
        param (int): The parameter value

    Returns:
        str: The friendly size description
    """
    intervals = [(0, 15), (15, 60), (60, 100), (100, 400), (400, float("inf"))]
    sizes = ["XS", "S", "M", "L", "XL"]

    for i, (lower, upper) in enumerate(intervals):
        if lower <= params < upper:
            return sizes[i]

    raise Exception("Error: Could not guess friendly_size")


def validate() -> None:
    raw_licenses = read_json(LICENSES_PATH)
    raw_orgas = read_json(MODELS_PATH)
    raw_extra_data = {m["model_name"]: m for m in read_json(MODELS_EXTRA_DATA_PATH)}
    raw_preferences_data = read_json(MODELS_PREFERENCES_PATH)

    dumped_licenses = validate_licenses(raw_licenses)

    if dumped_licenses is None:
        log.error("Errors in 'licenses.json', exiting...")
        return
    else:
        log.info("No errors in 'licenses.json'!")

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

    # First validate with RawOrgas
    dumped_orgas = validate_orgas_and_models(raw_orgas)

    if dumped_orgas is None:
        log.error("Errors in 'models.json', exiting...")
        return
    else:
        log.info("No errors in 'models.json'!")

    context = {
        "licenses": {l["license"]: l for l in dumped_licenses},
        "data": raw_extra_data,
    }

    # Then use the full Orgas builder
    # Any errors comming from here are code generation errors, not errors in 'models.json'
    orgas = Orgas.model_validate(raw_orgas, context=context)

    generated_models = {}

    i18n = {
        "licenses": {
            "os": {
                l["license"]: {
                    k: (
                        (l[k] if k in l else "")
                        if k != "license_desc"
                        else markdown.markdown(l[k])
                    )
                    for k in I18N_OS_LICENSE_KEYS
                }
                for l in context["licenses"].values()
                if l["license"] != "proprietary"
            },
            "proprio": {},
        },
        "models": {},
    }

    # Load existing generated models to pass to get_ecologits_rate
    existing_generated_models = read_json(GENERATED_MODELS_PATH)

    if os.getenv("DATABASE_URI"):
        engine = connect_to_db(os.getenv("DATABASE_URI"))
        fetch_distinct_model_ids(engine, existing_generated_models)

    # FIXME temp
    return

    wh_per_million_token_map = get_ecologits_rate(existing_generated_models)

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
                model_data["distribution"] = "fully-open-source"

            model_data["friendly_size"] = params_to_friendly_size(model_data["params"])

            if model.get("quantization", None) == "q8":
                model_data["required_ram"] = model_data["params"] * 2
            else:
                # We suppose from q4 to fp16
                model_data["required_ram"] = model_data["params"]

            model_extra_data = next(
                (
                    m
                    for m in raw_extra_data
                    if m["model_name"] == model["id"]
                    # or m["name"] == model["simple_name"]
                ),
                None,
            )
            # FIXME check whos missing
            if model_extra_data is not None:
                model_extra_data = {
                    "elo": round(model_extra_data["median"]),
                    # trust range based on computed median rank and interval
                    "trust_range": [
                        model_extra_data["rank"] - model_extra_data["rank_p2.5"],
                        model_extra_data["rank_p97.5"] - model_extra_data["rank"],
                    ],
                    "n_match": model_extra_data["n_match"],
                    "mean_win_prob": model_extra_data["mean_win_prob"],
                    "win_rate": model_extra_data["win_rate"],
                    "consumption_wh": round(
                        model_extra_data["mean_conso_per_token"] * 1000 * 1000
                    ),
                }

            model_preferences_data = next(
                (m for m in raw_preferences_data if m["model_name"] == model["id"]),
                None,
            )
            # FIXME check whos missing
            if model_preferences_data is not None:
                model_preferences_data = {
                    k: v for k, v in model_preferences_data.items() if k != "model_name"
                }

            # Build complete model data (license + model) without translatable keys
            generated_models[model["id"]] = sort_dict(
                {
                    **filter_dict(license_data, I18N_OS_LICENSE_KEYS),
                    **model_data,
                    **(model_extra_data or {}),
                    "prefs": model_preferences_data,
                    "wh_per_million_token": wh_per_million_token_map.get(
                        model["id"], 0
                    ),
                }
            )

    i18n["licenses"]["proprio"] = sort_dict(i18n["licenses"]["proprio"])
    i18n["models"] = sort_dict(i18n["models"])

    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(I18N_PATH)
    frontend_i18n["generated"] = sort_dict(i18n)

    # FIXME add ARCHS
    TS_DATA_PATH.write_text(
        f"""export const LICENSES = {[license["license"] for license in dumped_licenses]} as const
export const ORGANISATIONS = {[orga["name"] for orga in dumped_orgas]} as const
export const MODELS = {[model["simple_name"] for model in generated_models.values()]} as const
"""
    )

    write_json(I18N_PATH, frontend_i18n, indent=4)
    write_json(GENERATED_MODELS_PATH, sort_dict(generated_models))


if __name__ == "__main__":
    validate()
