import datetime
import logging
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


def main(fetch_latest_dataset_results: bool = True) -> None:
    raw_orgas = read_json(LLMS_RAW_DATA_FILE)

    # First validate base data
    try:
        licenses = get_licenses()
        dumped_archs = get_archs()
        context = {
            "licenses": {l["license"]: l for l in licenses.model_dump()},
            "archs": {a.pop("id"): a for a in dumped_archs},
        }
        dumped_orgas = validate_orgas_and_models(raw_orgas, context=context)
    except Exception as err:
        if str(err).startswith("Errors in"):
            logger.error(str(err))
        else:
            logger.exception(err)
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

    # Integrate translatable content to frontend locales
    frontend_i18n = read_json(FRONTEND_MAIN_I18N_FILE)
    frontend_i18n["generated"] = sort_dict(i18n)
    write_json(FRONTEND_MAIN_I18N_FILE, frontend_i18n, indent=4)

    # Save generated models
    write_json(
        LLMS_GENERATED_DATA_FILE,
        {
            "timestamp": datetime.datetime.now().timestamp(),
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
