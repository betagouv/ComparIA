import logging
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError

from utils.logger import log_pydantic_parsed_errors
from utils.utils import (
    DATA_DIR,
    FRONTEND_MAIN_I18N_FILE,
    read_json,
    sort_dict,
    write_json,
)

logger = logging.getLogger("comparia.internal")

ARCHS_FILE = DATA_DIR / "archs.json"
ARCHS_SCHEMA_FILE = DATA_DIR / "generated" / "schema-archs.json"

descs = {
    "id": "Architecture identifier (e.g. 'dense', 'moe')",
    "name": "Human-readable architecture name",
    "long_name": "Human-readable architecture complete name (e.g: 'Mixture of Experts')",
    "desc": "Detailed description of the architecture",
}


# LLM architecture definitions
class Arch(BaseModel):
    """
    LLM architecture definition.

    Defines LLMs architecture and properties.
    Used to validate `utils/models/archs.json`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(description=descs["id"])]
    name: Annotated[str, Field(description=descs["name"])]
    long_name: Annotated[str, Field(description=descs["long_name"])]
    desc: Annotated[str, Field(description=descs["desc"])]


Archs = RootModel[list[Arch]]


def get_archs() -> Archs:
    try:
        return read_json(ARCHS_FILE, Archs)
    except ValidationError as exc:
        errors: dict[str, list[dict[str, Any]]] = {}

        for err in exc.errors():
            idx, key = err["loc"]
            name = f"arch '{idx}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": key, **err})

        log_pydantic_parsed_errors(logger, errors)

        raise Exception("Errors in 'archs.json', exiting...")


def generate_archs_i18n() -> None:
    archs = get_archs()

    frontend_i18n = read_json(FRONTEND_MAIN_I18N_FILE)
    frontend_i18n["generated"]["archs"] = sort_dict(
        {a.pop("id"): a for a in archs.model_dump()}
    )
    write_json(FRONTEND_MAIN_I18N_FILE, frontend_i18n, indent=4)


def generate_archs_json_schema() -> None:
    write_json(ARCHS_SCHEMA_FILE, Archs.model_json_schema())
