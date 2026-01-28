import logging
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

from backend.llms.models import Distribution
from utils.logger import configure_logger, log_pydantic_parsed_errors
from utils.utils import MarkdownSerializer, read_json

logger = configure_logger(logging.getLogger("llms:licenses"))

LICENSES_FILE = Path(__file__).parent / "licenses.json"


# License definitions for models
class License(BaseModel):
    """
    License metadata for a model.

    Defines licensing terms, distribution restrictions, and permitted uses.
    Used to validate 'utils/models/licenses.json'.

    Attributes:
        license: License identifier (e.g., "apache-2.0", "mit", "proprietary")
        license_desc: Human-readable description of the license
        distribution: How model is distributed (api-only, open-weights, fully-open-source)
        reuse: Whether model can be reused/redistributed
        commercial_use: Whether commercial use is permitted (None = unknown)
        reuse_specificities: Additional reuse restrictions/notes
        commercial_use_specificities: Additional commercial use restrictions/notes
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    license: str
    license_desc: Annotated[str, MarkdownSerializer]
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = ""
    commercial_use_specificities: str | None = ""


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
