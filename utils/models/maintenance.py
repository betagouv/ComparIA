from datetime import date
from rich import print
from build_models import (
    MODELS_PATH,
    validate_orgas_and_models,
    log,
)
from utils import read_json, write_json, filter_dict, sort_dict


def clean_models():
    raw_orgas = read_json(MODELS_PATH)
    filtered_out_models = {}

    # Filter out some models based on attr `status`
    for orga in raw_orgas:
        filtered_models = []
        for model in orga["models"]:
            if model.get("status", None) == "missing_data":
                if not orga["name"] in filtered_out_models:
                    filtered_out_models[orga["name"]] = []
                filtered_out_models[orga["name"]].append(model)
            else:
                filtered_models.append(model)
        orga["models"] = filtered_models

    dumped_orgas = validate_orgas_and_models(raw_orgas, exclude_defaults=True)

    if not dumped_orgas:
        log.error("Something went wrong, aborting…")
        return

    for orga in dumped_orgas:
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
        orga = next((orga for orga in dumped_orgas if orga["name"] == name))
        orga["models"] = models + orga["models"]

    write_json(MODELS_PATH, dumped_orgas)


if __name__ == "__main__":
    clean_models()
