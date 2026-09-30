import json
import logging
from pathlib import Path
from typing import Any, TypeVar, overload

import markdown
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, FieldSerializationInfo, PlainSerializer
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue

from utils.logger import configure_logger

Obj = dict[str, Any]

UTILS_DIR = Path(__file__).parent
ROOT_DIR = UTILS_DIR.parent
DATA_DIR = ROOT_DIR / "data"
# LLMs data
DEFAULT_LLM_DATA_PATH = DATA_DIR / "llms-data.json"
# Frontend
MAIN_LOCALE = "fr"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_I18N_DIR = FRONTEND_DIR / "locales" / "messages"
FRONTEND_MAIN_I18N_FILE = FRONTEND_I18N_DIR / f"{MAIN_LOCALE}.json"
FRONTEND_GENERATED_DIR = FRONTEND_DIR / "src" / "lib" / "generated"

# Legacy LLM files (be carefull to not remove those file, needed in migrations)
LEGACY_DATA_DIR = DATA_DIR / "legacy"
LLMS_RAW_DATA_FILE = LEGACY_DATA_DIR / "models.json"
LLMS_LICENSES_FILE = LEGACY_DATA_DIR / "licenses.json"
LLMS_GENERATED_DATA_FILE = (
    LEGACY_DATA_DIR / "generated-models.json"
)  # FIXME to rm at some point

logger = configure_logger(logging.getLogger("utils"))

# Serializers


def to_markdown(v: str, info: FieldSerializationInfo) -> str:
    return v if info.mode == "json" else markdown.markdown(v)


MarkdownSerializer = PlainSerializer(to_markdown, when_used="unless-none")

# Helpers

TModel = TypeVar("T", bound=BaseModel)


@overload
def read_json(path: Path) -> Any: ...
@overload
def read_json(path: Path, model: type[TModel]) -> TModel: ...
def read_json(path: Path, model: type[TModel] | None = None) -> Any:
    """
    Read json data from file.
    If given a pydantic model, will validate and return specified object
    """
    logger.debug(f"Reading '{path.relative_to(ROOT_DIR)}'...")
    data = json.loads(path.read_text())
    logger.info(f"Successfully read '{path.relative_to(ROOT_DIR)}'!")

    if model:
        data = model.model_validate(data)
        logger.info(f"Successfully validated '{path.relative_to(ROOT_DIR)}'!")

    return data


def write_json(
    path: Path,
    data: dict[str, Any] | list[Any] | BaseModel,
    indent: int = 2,
    sort_keys: bool = False,
) -> None:
    """
    Serialize and writes data to json file.
    """
    logger.debug(f"Saving '{path.relative_to(ROOT_DIR)}'...")

    if sort_keys or not isinstance(data, BaseModel):
        data = jsonable_encoder(
            data.model_dump() if isinstance(data, BaseModel) else data
        )
        json_data = json.dumps(
            data, ensure_ascii=False, indent=indent, sort_keys=sort_keys
        )
    else:
        json_data = data.model_dump_json(ensure_ascii=False, indent=indent)

    path.write_text(json_data + "\n")
    logger.info(f"Successfully saved '{path.relative_to(ROOT_DIR)}'!")


def filter_dict(data: Obj, exclude: list[str]) -> Obj:
    return {k: data[k] for k in set(data.keys()).difference(exclude)}


def sort_dict(data: Obj, deep: bool = True) -> Obj:
    items = [
        (key, sort_dict(value) if isinstance(value, dict) else value)
        for key, value in data.items()
    ]

    return dict(sorted(items, key=lambda i: i[0].lower()))


class FormJsonSchema(GenerateJsonSchema):
    def sort(
        self, value: JsonSchemaValue, parent_key: str | None = None
    ) -> JsonSchemaValue:
        # Do not sort at all, form will be displayed based on attribute order
        return value

    def get_flattened_anyof(self, schemas: list[JsonSchemaValue]) -> JsonSchemaValue:
        # remove null values for simplicity, inject 'optional' prop if null in schemas
        non_null = [schema for schema in schemas if schema["type"] != "null"]
        flattened = super().get_flattened_anyof(schemas=non_null)
        if len(schemas) != len(non_null):
            flattened["optional"] = True
        return flattened
