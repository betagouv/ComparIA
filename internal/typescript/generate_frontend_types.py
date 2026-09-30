import re
from typing import get_args

from pydantic2ts import generate_typescript_defs

from backend.llms.models import ENERGY_CLASSES, SIZE_CLASSES
from internal.archs import get_archs
from utils.database.models.llms.constants import LLMArchKind
from utils.utils import FRONTEND_DIR, FRONTEND_GENERATED_DIR

JSON2TS_PATH = FRONTEND_DIR / "node_modules/.bin/json2ts"
FRONTEND_TYPES = FRONTEND_GENERATED_DIR / "backend.ts"
FRONTEND_ADMIN_TYPES = FRONTEND_GENERATED_DIR / "admin.ts"
FRONTEND_CONSTANTS = FRONTEND_GENERATED_DIR / "constants.ts"


def generate_frontend_types():
    generate_typescript_defs(
        "internal.typescript.backend_types",
        str(FRONTEND_TYPES),
        json2ts_cmd=str(JSON2TS_PATH.absolute()),
    )
    generate_typescript_defs(
        "internal.typescript.admin_types",
        str(FRONTEND_ADMIN_TYPES),
        json2ts_cmd=str(JSON2TS_PATH.absolute()),
    )


def to_pascal_case(s: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[_\-\s]+", s.lower()))


def generate_frontend_constants() -> None:
    archs = [arch.id for arch in get_archs().root]

    backend_archs = [kind for kind in get_args(LLMArchKind) if "maybe-" not in kind]
    if extra_archs := set(backend_archs).symmetric_difference(archs):
        raise ValueError(
            f"Backend and json archs are not the same, extra archs: {extra_archs}"
        )

    constants = {
        "SIZE_CLASSES": list(SIZE_CLASSES),
        "ENERGY_CLASSES": list(ENERGY_CLASSES),
        "ARCHS": archs,
        "MAYBE_ARCHS": [f"maybe-{a}" for a in archs if a != "na"],
    }

    file_lines = [f"export const {k} = {v} as const" for k, v in constants.items()] + [
        f"export type {to_pascal_case(k)} = (typeof {k})[number]"
        for k, v in constants.items()
    ]

    FRONTEND_CONSTANTS.write_text("\n".join(file_lines) + "\n")
