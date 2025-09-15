import tomli
import json
from typing import Literal
from pydantic import BaseModel, RootModel
from rich import print
from pathlib import Path
from slugify import slugify
from build_models import (
    Model,
    GENERATED_MODELS_PATH,
    MODELS_PATH,
    params_to_friendly_size,
)
from utils import read_json, write_json

CURRENT_FOLDER = Path(__file__).parent
ROOT_FOLDER = Path(__file__).parent.parent.parent

size_desc = {
    "XS": "Les modèles très petits, avec moins de 7 milliards de paramètres, sont les moins complexes et les plus économiques en termes de ressources, offrant des performances suffisantes pour des tâches simples comme la classification de texte.",
    "S": "Un modèle de petit gabarit est moins complexe et coûteux en ressources par rapport aux modèles plus grands, tout en offrant une performance suffisante pour diverses tâches (résumé, traduction, classification de texte...)",
    "M": "Les modèles moyens offrent un bon équilibre entre complexité, coût et performance : ils sont beaucoup moins consommateurs de ressources que les grands modèles tout en étant capables de gérer des tâches complexes telles que l'analyse de sentiment ou le raisonnement.",
    "L": "Les grands modèles nécessitent des ressources significatives, mais offrent les meilleures performances pour des tâches avancées comme la rédaction créative, la modélisation de dialogues et les applications nécessitant une compréhension fine du contexte.",
    "XL": "Ces modèles dotés de plusieurs centaines de milliards de paramètres sont les plus complexes et avancés en termes de performance et de précision. Les ressources de calcul et de mémoire nécessaires pour déployer ces modèles sont telles qu’ils sont destinés aux applications les plus avancées et aux environnements hautement spécialisés.",
}


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
    status: Literal["archived"]
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
    fp = ROOT_FOLDER / "models-extra-info.toml"
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
                "fully_open_source",
            )
        }
        reformated_model["status"] = "archived"
        reformated_model["params"] = model.get(
            "total_params", model.get("params", model.get("friendly_size"))
        )
        reformated_model["desc"] = model.get("excerpt")
        reformated_model["fyi"] = model.get("description")
        friendly_size = model.get("friendly_size") or params_to_friendly_size(
            reformated_model["params"]
        )
        reformated_model["size_desc"] = size_desc[friendly_size]

        orga["models"].append(
            NewModel(**reformated_model).model_dump(exclude_defaults=True)
        )

    write_json(MODELS_PATH, orgas)


def migrate_models_id():
    orgas = read_json(MODELS_PATH)

    for orga in orgas:
        orga["models"] = [
            model if model.get("id") else {"id": slugify(model["simple_name"]), **model}
            for model in orga["models"]
        ]

    write_json(MODELS_PATH, orgas)


def migrate_api_endpoint_file():
    register_api_endpoint_file_path = ROOT_FOLDER / "register-api-endpoint-file.json"
    models_api_data = read_json(register_api_endpoint_file_path)
    orgas = read_json(MODELS_PATH)

    for orga in orgas:
        for model in orga["models"]:
            if model.get("status", None):
                continue

            api_data = next(
                (
                    api_data
                    for api_data in models_api_data
                    if api_data["model_id"] == model["id"]
                ),
                None,
            )

            if not api_data:
                print(
                    f"Missing endpoint data in `register-api-endpoint-file.json` for model '{model['id']}', skipping"
                )
                model["status"] = "missing_data"
                continue

            model["endpoint"] = {}
            model["endpoint"]["api_model_id"] = api_data["model_name"]

            if api_data.get("api_type") != "openai":
                model["endpoint"]["api_type"] = api_data["api_type"]
            if api_data.get("api_base"):
                model["endpoint"]["api_base"] = api_data["api_base"]

    write_json(MODELS_PATH, orgas)


if __name__ == "__main__":
    # migrate_old_models_to_new_format() # migrated: 15/09/2025
    # migrate_models_id() # migrated: 15/09/2025
    migrate_api_endpoint_file()
