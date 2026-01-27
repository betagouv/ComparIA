import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import read_json

logger = configure_logger(logging.getLogger("llms:archs"))

ARCHS_FILE = Path(__file__).parent / "archs.json"


# Model architecture definitions
class Arch(BaseModel):
    """
    Model architecture information.

    Defines neural network architecture and properties.
    Used to validate 'utils/models/arch/archs.json'.

    Attributes:
        id: Architecture identifier (e.g., "transformer", "moe")
        name: Short name
        title: Display title
        desc: Detailed description of the architecture
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    title: str
    desc: str


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
