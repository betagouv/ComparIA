import logging
import os
import sys

from utils.logger import configure_logger
from utils.utils import (
    FRONTEND_GENERATED_DIR,
    FRONTEND_MAIN_I18N_FILE,
    LLMS_GENERATED_DATA_FILE,
    read_json,
    sort_dict,
    write_json,
)

from .archs import get_archs
from .dataset_data import (
    LLMS_DATASET_DATA_FILE,
    fetch_and_save_ranking_results,
    get_dataset_data,
)
from .licenses import get_licenses
from .organisations import LLMS_RAW_DATA_FILE, Orgas, validate_orgas_and_models

logger = configure_logger(logging.getLogger("llms"))

TS_DATA_FILE = FRONTEND_GENERATED_DIR / "models.ts"
I18N_OS_LICENSE_KEYS = {
    "license_desc",
    "reuse_specificities",
    "commercial_use_specificities",
}
I18N_MODEL_KEYS = {"desc", "size_desc", "fyi"}


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


def main(fetch_latest_dataset_results: bool = True) -> None:
    # Fetch the latest dataset results from ranking pipelinerepo
    if fetch_latest_dataset_results:
        fetch_and_save_ranking_results()

    raw_orgas = read_json(LLMS_RAW_DATA_FILE)
    raw_dataset_data = read_json(LLMS_DATASET_DATA_FILE)

    # First validate base data
    try:
        licenses = get_licenses()
        dumped_archs = get_archs()
        dataset_data = get_dataset_data(raw_dataset_data)
        context = {
            "licenses": {l["license"]: l for l in licenses.model_dump()},
            "archs": {a.pop("id"): a for a in dumped_archs},
            "data": dataset_data.models,
        }
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
                l.license: l.model_dump(include=I18N_OS_LICENSE_KEYS)
                for l in licenses.root
                if l.license != "proprietary"
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
        i18n["licenses"]["proprio"][orga.name] = orga.model_dump(
            include=I18N_OS_LICENSE_KEYS
        )

        for model in orga.models:
            # Retrieving i18n models descriptions
            i18n["models"][model.simple_name] = model.model_dump(
                include=I18N_MODEL_KEYS
            )

            generated_models[model.id] = model.model_dump(exclude=I18N_MODEL_KEYS)

    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(FRONTEND_MAIN_I18N_FILE)
    frontend_i18n["generated"] = sort_dict(i18n)
    write_json(FRONTEND_MAIN_I18N_FILE, frontend_i18n, indent=4)

    # Save generated models

    write_json(
        LLMS_GENERATED_DATA_FILE,
        {
            "timestamp": dataset_data.timestamp,
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


if __name__ == "__main__":
    main()
