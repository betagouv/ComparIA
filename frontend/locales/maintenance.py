import glob
import json
from pathlib import Path
from typing import Any

CURRENT_FOLDER = Path(__file__).parent
LOCALES_FOLDER = CURRENT_FOLDER / "messages"
FR_I18N_PATH = LOCALES_FOLDER / "fr.json"

LOCALE_FILES = {
    path.split("/")[-1].replace(".json", ""): path
    for path in glob.glob(str(LOCALES_FOLDER) + "/*.json")
}
ALL_LOCALES = set(LOCALE_FILES.keys())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, data, indent: int = 4) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")


def sort_dict(data: dict[str, Any], deep: bool = True) -> dict[str, Any]:
    items = [
        (key, sort_dict(value) if isinstance(value, dict) else value)
        for key, value in data.items()
    ]

    return dict(sorted(items, key=lambda i: i[0].lower()))


def get_flatten_keys(d: dict[str, Any], parent_key="") -> set[str]:
    items: set[str] = set()

    for k, v in d.items():
        key = f"{parent_key}.{k}" if parent_key else k

        if isinstance(v, dict):
            items |= get_flatten_keys(v, key)

        items.add(key)

    return items


def filter_data(data: dict[str, Any], stale_keys: set[str]) -> dict[str, Any]:
    filtered = {}

    for k, v in data.items():
        if k not in stale_keys:
            value = v

            if isinstance(v, dict):
                nested_stale_keys = set(
                    [
                        key.replace(f"{k}.", "")
                        for key in stale_keys
                        if key.startswith(f"{k}.")
                    ]
                )
                if nested_stale_keys:
                    value = filter_data(v, nested_stale_keys)

            filtered[k] = value

    return filtered


def remove_stale_keys(ref_keys: set[str], locales: set[str]):
    for locale in locales:
        LOCALE_FILE = LOCALES_FOLDER / f"{locale}.json"
        data = read_json(LOCALE_FILE)
        keys = get_flatten_keys(data)
        stale_keys = set(sorted(keys - ref_keys))

        if stale_keys:
            print(f"Stale keys detected in '{locale}.json', removing...")
            for key in stale_keys:
                print(f"- {key}")

        filtered_data = filter_data(data, stale_keys)
        write_json(LOCALE_FILE, filtered_data)


if __name__ == "__main__":
    locales = ALL_LOCALES
    locales.discard("fr")

    # Remove fr.json no longer present keys in other locales files
    fr_data = read_json(FR_I18N_PATH)
    remove_stale_keys(get_flatten_keys(fr_data), locales)
    # Also sort fr.json
    write_json(FR_I18N_PATH, sort_dict(fr_data))
