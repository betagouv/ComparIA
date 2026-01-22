from datetime import date

from backend.llms.models import Archs, Licenses, RawOrgas
from utils.models.build_models import (
    ARCHS_PATH,
    LICENSES_PATH,
    MODELS_PATH,
    log,
    validate_orgas_and_models,
)
from utils.models.utils import read_json, write_json


def clean_models():
    # Clean models.json
    # put 'missing_data' models first in list
    # reorder models based on date (most recent first)
    # remove keys that are default values

    context = {
        "licenses": {
            l["license"]: l
            for l in Licenses(read_json(LICENSES_PATH)).model_dump(exclude_none=True)
        },
        "archs": {a.pop("id"): a for a in Archs(read_json(ARCHS_PATH)).model_dump()},
    }

    raw_orgas = read_json(MODELS_PATH)
    filtered_out_models = {}

    # Filter out some models based on attr `status`
    for orga in raw_orgas:
        filtered_models = []
        for model in orga["models"]:
            if model.get("status", None) == "missing_data":
                print(f"Warning: Missing model data for '{model["id"]}'")
                if not orga["name"] in filtered_out_models:
                    filtered_out_models[orga["name"]] = []
                filtered_out_models[orga["name"]].append(model)
            else:
                filtered_models.append(model)
        orga["models"] = filtered_models

    orgas = RawOrgas.model_validate(raw_orgas, context=context).model_dump(
        exclude_defaults=True
    )

    for orga in orgas:
        orga["models"] = sorted(
            orga["models"],
            key=lambda m: date(
                int(m["release_date"].split("/")[1]),
                int(m["release_date"].split("/")[0]),
                1,
            ),
            reverse=True,
        )

    # Reinject non validated models
    for name, models in filtered_out_models.items():
        orga = next((orga for orga in orgas if orga["name"] == name))
        orga["models"] = orga["models"] + models

    write_json(MODELS_PATH, orgas)


if __name__ == "__main__":
    clean_models()
