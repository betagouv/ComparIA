from pydantic import BaseModel, Field, RootModel

from utils.models.build_models import (
    CURRENT_FOLDER,
    GENERATED_MODELS_PATH,
    ROOT_PATH,
    log,
)
from utils.utils import read_json, write_json

SIMPLIFIED_LLM_DATA_OUTPUT_PATH = (
    CURRENT_FOLDER.parent / "ranking_methods" / "data" / "models_data.json"
)

class SimplifiedLLM(BaseModel):
    name: str = Field(validation_alias="simple_name")
    model_name: str = Field(validation_alias="id")
    organization: str = Field(validation_alias="organisation")
    license: str


SimplifiedLLMList = RootModel[list[SimplifiedLLM]]


def main() -> None:
    # Generate model list based on generated models to avoid errors (data is supposed to be valid)
    raw_models = [
        model for model
        in read_json(GENERATED_MODELS_PATH)["models"].values()
    ]
    models = SimplifiedLLMList(raw_models).model_dump()

    write_json(SIMPLIFIED_LLM_DATA_OUTPUT_PATH, models, indent=2)

    log.info(
        f"Generation of '{SIMPLIFIED_LLM_DATA_OUTPUT_PATH.relative_to(ROOT_PATH)}' is successfull!"
    )


if __name__ == "__main__":
    main()
