import logging
import os
import pickle
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import Connection, create_engine

logger = logging.getLogger("comparia.db.migrate")

NOT_ARCHIVED = "archived IS NOT TRUE"


def ensure_maps_dir(maps_dir: str) -> None:
    os.makedirs(maps_dir, exist_ok=True)


def save_map(maps_dir: str, name: str, data: Any) -> None:
    path = os.path.join(maps_dir, f"{name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"Saved {name}: {len(data)} entries → {path}")


def load_map(maps_dir: str, name: str) -> Any:
    path = os.path.join(maps_dir, f"{name}.pkl")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required map '{name}' not found at {path}. "
            f"Run the prerequisite migration step first."
        )
    with open(path, "rb") as f:
        data = pickle.load(f)
    logger.info(f"Loaded {name}: {len(data)} entries from {path}")
    return data


@contextmanager
def source_connection(source_uri: str, stream: bool = False) -> Generator[Connection, None, None]:
    engine = create_engine(source_uri, execution_options={"stream_results": stream})
    try:
        with engine.connect() as conn:
            yield conn
    finally:
        engine.dispose()


def bool_flags_to_keywords(row: dict, columns: list[str]) -> list[str]:
    return [col for col in columns if row.get(col)]
