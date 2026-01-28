from datetime import date

from utils.models.build_models import LLMS_RAW_DATA_FILE
from utils.utils import read_json, write_json

from .archs import get_archs
from .licenses import get_licenses
from .organisations import RawOrgas


def clean_models():
    # Clean models.json
    # put 'missing_data' models first in list
    # reorder models based on date (most recent first)
    # remove keys that are default values

    context = {
        "licenses": {l.license: l for l in get_licenses().root},
        "archs": {a.pop("id"): a for a in get_archs()},
    }

    raw_orgas = read_json(LLMS_RAW_DATA_FILE)
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

    write_json(LLMS_RAW_DATA_FILE, orgas)


if __name__ == "__main__":
    clean_models()
