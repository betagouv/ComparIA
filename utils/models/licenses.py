import logging
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError

from backend.llms.models import Distribution
from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import MarkdownSerializer, read_json

logger = configure_logger(logging.getLogger("llms:licenses"))

LICENSES_FILE = Path(__file__).parent / "licenses.json"


descs = {
    "license": "Human-readable License name (e.g. 'Apache 2.0' or 'MIT')",
    "license_desc": "Description of the license",
    "distribution": "How the LLM is distributed",
    "reuse": "Whether the LLM can be reused/redistributed",
    "commercial_use": "Whether commercial use is permitted (None = unknown)",
    "reuse_specificities": "Additional reuse restrictions/notes",
    "commercial_use_specificities": "Additional commercial use restrictions/notes",
}


# License definitions for LLMs
class License(BaseModel):
    """
    License metadata for a LLM.

    Defines licensing terms, distribution restrictions, and permitted uses.
    Used to validate `utils/models/licenses.json`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    license: Annotated[str, Field(description=descs["license"])]
    license_desc: Annotated[
        str, MarkdownSerializer, Field(description=descs["license_desc"])
    ]
    distribution: Annotated[Distribution, Field(description=descs["distribution"])]
    reuse: Annotated[bool, Field(description=descs["reuse"])]
    commercial_use: Annotated[
        bool | None, Field(description=descs["commercial_use"])
    ] = None
    reuse_specificities: Annotated[
        str | None, Field(description=descs["reuse_specificities"])
    ] = ""
    commercial_use_specificities: Annotated[
        str | None, Field(description=descs["commercial_use_specificities"])
    ] = ""


Licenses = RootModel[list[License]]


def get_licenses() -> Licenses:
    raw_licenses = read_json(LICENSES_FILE)

    try:
        licenses = Licenses(raw_licenses)
        logger.info("No errors in 'licenses.json'!")
        return licenses
    except ValidationError as exc:
        errors: dict[str, list[dict[str, Any]]] = {}

        for err in exc.errors():
            idx, key = err["loc"]
            name = f"license '{raw_licenses[idx].get("license", idx)}'"
            if name not in errors:
                errors[name] = []
            errors[name].append({"key": err["loc"][1], **err})

        log_pydantic_parsed_errors(logger, errors)

        raise Exception("Errors in 'licenses.json', exiting...")
