import logging
import markdown
import os
from pathlib import Path
from pydantic import ValidationError
from rich.logging import RichHandler
from typing import Any

from languia.models import ROOT_PATH, Archs, Licenses, Orgas, RawOrgas
from utils.models.utils import Obj, read_json, write_json, sort_dict

logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="|", handlers=[RichHandler()]
)
log = logging.getLogger("models")

CURRENT_FOLDER = Path(__file__).parent
FRONTEND_FOLDER = CURRENT_FOLDER.parent.parent / "frontend"
LICENSES_PATH = CURRENT_FOLDER / "licenses.json"
ARCHS_PATH = CURRENT_FOLDER / "archs.json"
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


def validate_licenses(raw_licenses: Any) -> list[Any]:
    try:
        licenses = Licenses(raw_licenses).model_dump(exclude_none=True)
        log.info("No errors in 'licenses.json'!")
        return licenses
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

        for err in exc.errors():
            name = f"license '{raw_licenses[err["loc"][0]]["license"]}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": err["loc"][1], **err})

        log_errors(errors)

        raise Exception("Errors in 'licenses.json', exiting...")


def validate_archs(raw_archs: Any) -> list[Any]:
    try:
        archs = Archs(raw_archs).model_dump()
        log.info("No errors in 'archs.json'!")
        return archs
    except ValidationError as exc:
        errors: dict[str, list[Obj]] = {}

        for err in exc.errors():
            name = f"arch '{raw_archs[err["loc"][0]]["id"]}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": err["loc"][1], **err})

        log_errors(errors)

        raise Exception("Errors in 'archs.json', exiting...")


def validate_orgas_and_models(raw_orgas: Any, context: dict[str, Any]) -> list[Any]:
    try:
        orgas = RawOrgas.model_validate(raw_orgas, context=context).model_dump()
        log.info("No errors in 'models.json'!")
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

        log_errors(errors)

        raise Exception("Errors in 'models.json', exiting...")


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


def main() -> None:
    raw_licenses = read_json(LICENSES_PATH)
    raw_archs = read_json(ARCHS_PATH)
    raw_orgas = read_json(MODELS_PATH)
    raw_extra_data = read_json(MODELS_EXTRA_DATA_PATH)
    raw_models_data = {m["model_name"]: m for m in raw_extra_data["models"]}

    try:
        dumped_licenses = validate_licenses(raw_licenses)
        dumped_archs = validate_archs(raw_archs)
    except Exception as err:
        log.error(str(err))
        return

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

    context = {
        "licenses": {l["license"]: l for l in dumped_licenses},
        "archs": {a.pop("id"): a for a in dumped_archs},
        "data": raw_models_data,
    }

    # First validate with RawOrgas
    try:
        dumped_orgas = validate_orgas_and_models(raw_orgas, context=context)
    except Exception as err:
        log.error(str(err))
        return

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

    if os.getenv("DATABASE_URI"):
        existing_generated_models = read_json(GENERATED_MODELS_PATH)
        engine = connect_to_db(os.getenv("DATABASE_URI"))
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

            if model.data is None or model.prefs is None:
                log.warning(
                    f"Missing data for model '{model.id}' (status: {model.status})"
                )

            generated_models[model.id] = model.model_dump(exclude=I18N_MODEL_KEYS)

    # Integrate translatable content to frontend locales
    log.info(f"Saving '{I18N_PATH.relative_to(ROOT_PATH)}'...")
    frontend_i18n = read_json(I18N_PATH)
    frontend_i18n["generated"] = sort_dict(i18n)
    write_json(I18N_PATH, frontend_i18n, indent=4)

    # Save generated models
    log.info(f"Saving '{GENERATED_MODELS_PATH.relative_to(ROOT_PATH)}'...")
    write_json(
        GENERATED_MODELS_PATH,
        {
            "timestamp": raw_extra_data["timestamp"],
            "models": sort_dict(generated_models),
        },
    )

    # FIXME add ARCHS
    TS_DATA_PATH.write_text(
        f"""export const LICENSES = {[l for l in context["licenses"].keys()]} as const
export const ARCHS = {[a for a in context["archs"]]} as const
export const MAYBE_ARCHS = {[f"maybe-{a}" for a in context["archs"] if a != 'na']} as const
export const ORGANISATIONS = {[orga["name"] for orga in dumped_orgas]} as const
export const MODELS = {[model["simple_name"] for model in generated_models.values()]} as const
"""
    )

    log.info("Generation is successfull!")


if __name__ == "__main__":
    main()
