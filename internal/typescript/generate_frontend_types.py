from pydantic2ts import generate_typescript_defs

from utils.utils import FRONTEND_DIR, FRONTEND_GENERATED_DIR

JSON2TS_PATH = FRONTEND_DIR / "node_modules/.bin/json2ts"


def generate_frontend_types():
    generate_typescript_defs(
        "internal.typescript.backend_types",
        str(FRONTEND_GENERATED_DIR / "backend.ts"),
        json2ts_cmd=str(JSON2TS_PATH.absolute()),
    )
