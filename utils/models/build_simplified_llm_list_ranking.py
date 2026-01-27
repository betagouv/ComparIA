from pydantic import BaseModel, Field, RootModel

from utils.models.build_models import log
from utils.utils import (
    LLMS_GENERATED_DATA_FILE,
    ROOT_DIR,
    UTILS_DIR,
    read_json,
    write_json,
)

SIMPLIFIED_LLM_DATA_OUTPUT_PATH = (
    UTILS_DIR / "ranking_methods" / "data" / "models_data.json"
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
        model for model in read_json(LLMS_GENERATED_DATA_FILE)["models"].values()
    ]
    models = SimplifiedLLMList(raw_models).model_dump()

    write_json(SIMPLIFIED_LLM_DATA_OUTPUT_PATH, models, indent=2)

    log.info(
        f"Generation of '{SIMPLIFIED_LLM_DATA_OUTPUT_PATH.relative_to(ROOT_DIR)}' is successfull!"
    )


if __name__ == "__main__":
    main()
