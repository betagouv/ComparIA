import logging
import os
import sys

from utils.logger import configure_logger
from utils.utils import (
    FRONTEND_GENERATED_DIR,
    FRONTEND_MAIN_I18N_FILE,
    LLMS_GENERATED_DATA_FILE,
    ROOT_DIR,
    get_db_engine,
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


def get_conversations_llm_ids() -> set[str]:
    """Get distinct model IDs from the conversations table."""

    import polars as pl

    query = "SELECT DISTINCT model_a_name as model_id FROM conversations UNION SELECT DISTINCT model_b_name as model_id FROM conversations"
    try:
        with get_db_engine().connect() as conn:
            df = pl.read_database(query=query, connection=conn)
            # Filter out None values if any
            model_ids = df["model_id"].drop_nulls().unique().to_list()

            if not model_ids:
                # log as error, this should not happen in prod
                logger.error("No model IDs found in the database.")
                return set()

            return set(model_ids)
    except Exception as e:
        logger.error(f"Failed to fetch distinct model IDs: {e}")
        raise e


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

    # Warn about missing llms definitions or dataset data
    llm_ids = set(generated_models.keys())
    new_llm_ids = set([id_ for id_ in llm_ids if generated_models[id_]["new"]])
    archived_llm_ids = set(
        [id_ for id_ in llm_ids if generated_models[id_]["status"] == "archived"]
    )
    dataset_llm_ids = set(context["data"].keys())

    if no_llm_for_data_ids := dataset_llm_ids.difference(llm_ids):
        # There is data for an LLM but its id cannot be found in LLM definitions
        # Can happen if we changed its id
        logger.error(
            f"There is dataset data for LLMs that are not defined in '{LLMS_RAW_DATA_FILE.relative_to(ROOT_DIR)}': {no_llm_for_data_ids}"
        )
    if no_data_ids := archived_llm_ids.difference(dataset_llm_ids):
        # Can't find data for an archived LLM, maybe we could drop it from our list since we have no data at all
        logger.warning(f"There is no dataset data for archived LLMs: {no_data_ids}")
    if no_data_ids := (llm_ids - new_llm_ids - archived_llm_ids).difference(
        dataset_llm_ids
    ):
        # Can't find data for an LLM that is not new or archived, is it too soon? Is there a problem with its endpoint?
        logger.warning(
            f"There is no dataset data for LLMs (excepting new and archived ones): {no_data_ids}"
        )
    if os.getenv("COMPARIA_DB_URI"):
        # If DB uri, try to find if there's some LLMs that do not ends up in dataset data
        in_db_but_no_data_ids = get_conversations_llm_ids().difference(dataset_llm_ids)
        if in_db_but_no_data_ids:
            logger.error(
                f"LLMs are in db but not in dataset data: {in_db_but_no_data_ids}"
            )

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

    # Save typescript types in frontend code
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
