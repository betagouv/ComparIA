import logging
import os
import sys
from pathlib import Path
from typing import Any

import markdown
import requests
from pydantic import ValidationError

from backend.llms.models import DatasetData, Orgas, PreferencesData, RawOrgas
from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import (
    FRONTEND_GENERATED_DIR,
    FRONTEND_MAIN_I18N_FILE,
    LLMS_GENERATED_DATA_FILE,
    ROOT_DIR,
    Obj,
    read_json,
    sort_dict,
    write_json,
)

from .archs import get_archs
from .licenses import LICENSES_FILE, get_licenses

logger = configure_logger(logging.getLogger("llms"))

CURRENT_DIR = Path(__file__).parent
LLMS_RAW_DATA_FILE = CURRENT_DIR / "models.json"
LLMS_EXTRA_DATA_FILE = CURRENT_DIR / "generated-models-extra-data.json"
LLMS_EXTRA_DATA_URL = "https://github.com/betagouv/ranking_methods/releases/latest/download/ml_final_data.json"
LLMS_PREFERENCES_FILE = CURRENT_DIR / "generated-preferences.json"
TS_DATA_FILE = FRONTEND_GENERATED_DIR / "models.ts"
I18N_OS_LICENSE_KEYS = [
    "license_desc",
    "reuse_specificities",
    "commercial_use_specificities",
]
I18N_PROPRIO_LICENSE_KEYS = ["proprietary_" + k for k in I18N_OS_LICENSE_KEYS]
I18N_MODEL_KEYS = ["desc", "size_desc", "fyi"]


def validate_orgas_and_models(raw_orgas: Any, context: dict[str, Any]) -> list[Any]:
    try:
        orgas = RawOrgas.model_validate(raw_orgas, context=context).model_dump()
        logger.info("No errors in 'models.json'!")
        return orgas
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

        log_pydantic_parsed_errors(logger, errors)

        raise Exception("Errors in 'models.json', exiting...")


def connect_to_db(COMPARIA_DB_URI):

    from sqlalchemy import create_engine

    if not COMPARIA_DB_URI:
        logger.error(
            "Cannot connect to the database: no $COMPARIA_DB_URI configuration provided."
        )

    try:
        engine = create_engine(COMPARIA_DB_URI)
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
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
                logger.warning("No model IDs found in the database.")
                return {}

            missing_models = []
            for model_id in model_ids:
                if model_id not in models_data:
                    missing_models.append(
                        f"'{model_id}' not found in generated-models.json"
                    )

            if missing_models:
                logger.warning(
                    "Pre-check found missing models in generated-models.json:"
                )
                for model in missing_models:
                    logger.warning(f"- {model}")
            return [model_id.lower() for model_id in model_ids]
    except Exception as e:
        logger.error(f"Failed to fetch distinct model IDs: {e}")
        return []


def main() -> None:
    # Fetch the latest dataset results from ranking pipelinerepo
    new_extra_data = fetch_ranking_results(LLMS_EXTRA_DATA_URL)

    if new_extra_data.get("models") and len(new_extra_data.get("models")) > 0:
        write_json(LLMS_EXTRA_DATA_FILE, new_extra_data)

    raw_orgas = read_json(LLMS_RAW_DATA_FILE)
    raw_extra_data = read_json(LLMS_EXTRA_DATA_FILE)
    raw_models_data = {m["model_name"]: m for m in raw_extra_data["models"]}

    try:
        dumped_licenses = get_licenses()
        dumped_archs = get_archs()
    except Exception as err:
        logger.error(str(err))
        sys.exit(1)

    # Filter out some models based on attr `status`
    for orga in raw_orgas:
        filtered_models = []
        for model in orga["models"]:
            if model.get("status", None) == "missing_data":
                logger.warning(
                    f"Model '{model["simple_name"]}' is deactivated (reason={model["status"]})"
                )
            else:
                filtered_models.append(model)
        orga["models"] = filtered_models

    context = {
        "licenses": {l["license"]: l for l in dumped_licenses},
        "archs": {a.pop("id"): a for a in dumped_archs},
        "data": raw_models_data,
    }

    # First validate with RawOrgas
    try:
        dumped_orgas = validate_orgas_and_models(raw_orgas, context=context)
    except Exception as err:
        logger.error(str(err))
        sys.exit(1)

    # Then use the full Orgas builder
    # Any errors comming from here are code generation errors, not errors in 'models.json'
    orgas = Orgas.model_validate(raw_orgas, context=context)
    generated_models = {}

    i18n = {
        "archs": context["archs"],
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

    if os.getenv("COMPARIA_DB_URI"):
        existing_generated_models = read_json(LLMS_GENERATED_DATA_FILE)
        engine = connect_to_db(os.getenv("COMPARIA_DB_URI"))
        fetch_distinct_model_ids(engine, existing_generated_models)

    for orga in orgas.root:
        # Retrieving i18n licenses descriptions
        i18n["licenses"]["proprio"][orga.name] = {
            k.replace("proprietary_", ""): v if v else ""
            for k, v in orga.model_dump(include=I18N_PROPRIO_LICENSE_KEYS).items()
        }

        for model in orga.models:
            # Retrieving i18n models descriptions
            i18n["models"][model.simple_name] = {
                k: markdown.markdown(v)
                for k, v in model.model_dump(include=I18N_MODEL_KEYS).items()
            }

            generated_models[model.id] = model.model_dump(exclude=I18N_MODEL_KEYS)

    # Check for missing data/prefs and log warnings
    missing_info_events = []
    for model in orgas.root:
        for m in model.models:
            missing_data_fields = []
            missing_prefs_fields = []
            reason_parts = []

            # Check if model exists in raw source data
            model_in_source = m.id in raw_models_data

            # Check if data is completely missing
            if m.data is None:
                if not model_in_source:
                    reason_parts.append(
                        f"model '{m.id}' not found in ml_final_data.json"
                    )
                else:
                    # Model exists but data couldn't be built - check what's in source
                    source_data = raw_models_data[m.id]
                    missing_dataset_fields = []
                    for field_name in DatasetData.model_fields.keys():
                        if (
                            field_name not in source_data
                            or source_data.get(field_name) is None
                        ):
                            missing_dataset_fields.append(field_name)
                    if missing_dataset_fields:
                        reason_parts.append(
                            f"missing data fields in source: {', '.join(missing_dataset_fields)}"
                        )
                    else:
                        reason_parts.append(
                            "data validation failed (check field types)"
                        )
            else:
                # Check for missing fields within data
                data_dict = m.data.model_dump() if hasattr(m.data, "model_dump") else {}
                for field_name in DatasetData.model_fields.keys():
                    if field_name not in data_dict or data_dict.get(field_name) is None:
                        missing_data_fields.append(field_name)
                if missing_data_fields:
                    reason_parts.append(
                        f"incomplete data fields: {', '.join(missing_data_fields)}"
                    )

            # Check if prefs is completely missing
            if m.prefs is None:
                if not model_in_source:
                    # Already reported model not in source
                    pass
                else:
                    # Model exists but prefs couldn't be built - check what's in source
                    source_data = raw_models_data[m.id]
                    missing_prefs_source_fields = []
                    for field_name in PreferencesData.model_fields.keys():
                        if (
                            field_name not in source_data
                            or source_data.get(field_name) is None
                        ):
                            missing_prefs_source_fields.append(field_name)
                    if missing_prefs_source_fields:
                        reason_parts.append(
                            f"missing prefs fields in source: {', '.join(missing_prefs_source_fields)}"
                        )
                    else:
                        reason_parts.append(
                            "prefs validation failed (check field types)"
                        )
            else:
                # Check for missing fields within prefs
                prefs_dict = (
                    m.prefs.model_dump() if hasattr(m.prefs, "model_dump") else {}
                )
                for field_name in PreferencesData.model_fields.keys():
                    if (
                        field_name not in prefs_dict
                        or prefs_dict.get(field_name) is None
                    ):
                        missing_prefs_fields.append(field_name)
                if missing_prefs_fields:
                    reason_parts.append(
                        f"incomplete prefs fields: {', '.join(missing_prefs_fields)}"
                    )

            if reason_parts:
                missing_info_events.append(
                    {
                        "id": m.id,
                        "status": m.status,
                        "reason": " | ".join(reason_parts),
                    }
                )

    # Sort: Enabled models first (False < True), then alphabetical by ID
    missing_info_events.sort(key=lambda x: (x["status"] != "enabled", x["id"]))

    for event in missing_info_events:
        logger.warning(
            f"Model '{event['id']}' (status: {event['status']}): {event['reason']}"
        )
    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(FRONTEND_MAIN_I18N_FILE)
    frontend_i18n["generated"] = sort_dict(i18n)
    write_json(FRONTEND_MAIN_I18N_FILE, frontend_i18n, indent=4)

    # Save generated models
    write_json(
        LLMS_GENERATED_DATA_FILE,
        {
            "timestamp": raw_extra_data["timestamp"],
            "models": sort_dict(generated_models),
        },
    )

    # FIXME add ARCHS
    TS_DATA_FILE.write_text(
        f"""export const LICENSES = {[l for l in context["licenses"].keys()]} as const
export const ARCHS = {[a for a in context["archs"]]} as const
export const MAYBE_ARCHS = {[f"maybe-{a}" for a in context["archs"] if a != 'na']} as const
export const ORGANISATIONS = {[orga["name"] for orga in dumped_orgas]} as const
export const MODELS = {[model["simple_name"] for model in generated_models.values()]} as const
export const ICONS = {[orga["icon_path"] for orga in dumped_orgas if not "." in orga["icon_path"]]}
"""
    )

    logger.info("Generation is successfull!")


def fetch_ranking_results(url) -> dict:
    """Fetch the latest dataset ranking results from GitHub Actions pipeline."""

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch ranking results from repo: {e}")
        # Return empty data structure if fetch fails
        return {"models": [], "timestamp": None}


if __name__ == "__main__":
    main()
