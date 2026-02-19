import logging
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError

from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import read_json

logger = configure_logger(logging.getLogger("llms:archs"))

ARCHS_FILE = Path(__file__).parent / "archs.json"

descs = {
    "id": "Architecture identifier (e.g. 'dense', 'moe')",
    "name": "Human-readable architecture name",
    "title": "Human-readable architecture complete title ('Architecture {name}')",
    "desc": "Detailed description of the architecture",
}


# LLM architecture definitions
class Arch(BaseModel):
    """
    LLM architecture definition.

    Defines neural network architecture and properties.
    Used to validate `utils/models/archs.json`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(description=descs["id"])]
    name: Annotated[str, Field(description=descs["name"])]
    title: Annotated[str, Field(description=descs["title"])]
    desc: Annotated[str, Field(description=descs["desc"])]


Archs = RootModel[list[Arch]]


def get_archs() -> list[Any]:
    raw_archs = read_json(ARCHS_FILE)

    try:
        archs = Archs(raw_archs).model_dump()
        logger.info("No errors in 'archs.json'!")
        return archs
    except ValidationError as exc:
        errors: dict[str, list[dict[str, Any]]] = {}

        for err in exc.errors():
            idx, key = err["loc"]
            name = f"arch '{raw_archs[idx].get("id", idx)}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": key, **err})

        log_pydantic_parsed_errors(logger, errors)

        raise Exception("Errors in 'archs.json', exiting...")
