import tomli
import json
from typing import Literal
from pydantic import BaseModel, RootModel
from rich import print
from pathlib import Path
from build_models import Model, GENERATED_MODELS_PATH, MODELS_PATH
from utils import read_json, write_json

CURRENT_FOLDER = Path(__file__).parent


class OldModel(BaseModel):
    id: str | None = None
    simple_name: str
    license: str
    release_date: str | None = None
    params: int | float | None = None
    active_params: int | float | None = None
    reasoning: bool | Literal["hybrid"] | None = None
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None

    description: str | None = None
    excerpt: str | None = None
    total_params: int | float | None = None
    friendly_size: Literal["XS", "S", "M", "L", "XL"] | None = None
    fully_open_source: bool | None = None
    organisation: str
    icon_path: str


# Equivalent of new 'Model' but with some optional field
class NewModel(BaseModel):
    deactivated: Literal["archived"]
    id: str
    simple_name: str
    license: str
    fully_open_source: bool | None = None
    release_date: str | None = None
    params: int | float | Literal["XS", "S", "M", "L", "XL"] | None = None
    active_params: int | float | None = None
    arch: str | None = None
    reasoning: bool | Literal["hybrid"] | None = None
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None
    desc: str | None = None
    size_desc: str | None = None
    fyi: str | None = None


OldModels = RootModel[list[OldModel]]


def migrate_old_models_to_new_format():
    fp = Path(__file__).parent.parent.parent / "models-extra-info.toml"
    new_models = read_json(GENERATED_MODELS_PATH)
    raw_old_models = tomli.loads(fp.read_text())
    filtered_raw_old_models = []

    for model_id, raw_model in raw_old_models.items():
        if model_id in new_models:
            print(f"Skipping model '{model_id}': already in new models")
        else:
            filtered_raw_old_models.append({**raw_model, "id": model_id})

    old_models = OldModels(filtered_raw_old_models).model_dump(exclude_defaults=True)
    orgas = read_json(MODELS_PATH)
    for model in old_models:
        orga = next(
            (orga for orga in orgas if orga["name"] == model["organisation"]),
            None,
        )
        if not orga:
            orga = {
                "name": model["organisation"],
                "icon_path": model["icon_path"],
                "models": [],
            }
            orgas.append(orga)

        reformated_model = {
            k: model.get(k, None)
            for k in (
                "id",
                "simple_name",
                "license",
                "release_date",
                "active_params",
                "reasoning",
                "quantization",
                "url",
            )
        }
        reformated_model["deactivated"] = "archived"
        reformated_model["params"] = model.get(
            "total_params", model.get("params", model.get("friendly_size"))
        )
        reformated_model["desc"] = model.get("excerpt")
        reformated_model["fyi"] = model.get("description")

        orga["models"].append(
            NewModel(**reformated_model).model_dump(exclude_defaults=True)
        )

    write_json(MODELS_PATH, orgas)


if __name__ == "__main__":
    migrate_old_models_to_new_format()
