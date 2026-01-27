import json
import logging
from pathlib import Path
from typing import Any

from utils.logger import configure_logger

Obj = dict[str, Any]

UTILS_DIR = Path(__file__).parent
ROOT_DIR = UTILS_DIR.parent
# LLMs data
LLMS_GENERATED_DATA_FILE = UTILS_DIR / "models" / "generated-models.json"
# Frontend
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_MAIN_I18N_FILE = FRONTEND_DIR / "locales" / "messages" / "fr.json"
FRONTEND_GENERATED_DIR = FRONTEND_DIR / "src" / "lib" / "generated"

logger = configure_logger(logging.getLogger("utils"))


def read_json(path: Path) -> Any:
    logger.debug(f"Reading '{path.relative_to(ROOT_DIR)}'...")
    data = json.loads(path.read_text())
    logger.info(f"Successfully read '{path.relative_to(ROOT_DIR)}'!")
    return data


def write_json(path: Path, data, indent: int = 2) -> None:
    logger.debug(f"Saving '{path.relative_to(ROOT_DIR)}'...")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")
    logger.info(f"Successfully saved '{path.relative_to(ROOT_DIR)}'!")


def filter_dict(data: Obj, exclude: list[str]) -> Obj:
    return {k: data[k] for k in set(data.keys()).difference(exclude)}


def sort_dict(data: Obj, deep: bool = True) -> Obj:
    items = [
        (key, sort_dict(value) if isinstance(value, dict) else value)
        for key, value in data.items()
    ]

    return dict(sorted(items, key=lambda i: i[0].lower()))
