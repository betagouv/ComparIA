import glob
from typing import Any

from utils.utils import (
    FRONTEND_I18N_DIR,
    FRONTEND_MAIN_I18N_FILE,
    MAIN_LOCALE,
    read_json,
    write_json,
)

LOCALE_FILES = {
    path.split("/")[-1].replace(".json", ""): path
    for path in glob.glob(str(FRONTEND_I18N_DIR) + "/*.json")
}
ALL_LOCALES = set(LOCALE_FILES.keys())


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
        LOCALE_FILE = FRONTEND_I18N_DIR / f"{locale}.json"
        data = read_json(LOCALE_FILE)
        keys = get_flatten_keys(data)
        stale_keys = set(sorted(keys - ref_keys))

        if stale_keys:
            print(f"Stale keys detected in '{locale}.json', removing...")
            for key in stale_keys:
                print(f"- {key}")

        filtered_data = filter_data(data, stale_keys)
        write_json(LOCALE_FILE, filtered_data, indent=4)


def clean_locales():
    """
    Remove stale keys in all locales files.
    """
    locales = ALL_LOCALES
    locales.discard(MAIN_LOCALE)

    # Remove {MAIN_LOCALE}.json no longer present keys in other locales files
    main_data = read_json(FRONTEND_MAIN_I18N_FILE)
    remove_stale_keys(get_flatten_keys(main_data), locales)
    # Also sort {MAIN_LOCALE}.json
    write_json(FRONTEND_MAIN_I18N_FILE, sort_dict(main_data), indent=4)
