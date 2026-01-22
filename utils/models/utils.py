import json
from pathlib import Path
from typing import Any

import json5

Obj = dict[str, Any]


def read_json(path: Path) -> Any:
    return json5.loads(path.read_text())


def write_json(path: Path, data, indent: int = 2) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")


def filter_dict(data: Obj, exclude: list[str]) -> Obj:
    return {k: data[k] for k in set(data.keys()).difference(exclude)}


def sort_dict(data: Obj, deep: bool = True) -> Obj:
    items = [
        (key, sort_dict(value) if isinstance(value, dict) else value)
        for key, value in data.items()
    ]

    return dict(sorted(items, key=lambda i: i[0].lower()))
