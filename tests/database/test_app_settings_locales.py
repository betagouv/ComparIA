import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ["LOG_FORMAT"] = "JSON"

from utils.database.models.app_settings import (
    DEFAULT_ENABLED_LOCALES,
    SUPPORTED_LOCALES,
    AppSettings,
    AppSettingsPatch,
)


def test_a_fresh_instance_only_enables_the_well_translated_locales() -> None:
    assert AppSettings().enabled_locales == list(DEFAULT_ENABLED_LOCALES)


def test_the_thinly_translated_locales_stay_off_until_an_admin_asks() -> None:
    # They remain patchable, they just aren't served to anyone by default.
    off_by_default = set(SUPPORTED_LOCALES) - set(DEFAULT_ENABLED_LOCALES)

    assert off_by_default == {"lt", "sv"}
    assert AppSettingsPatch(enabled_locales=["fr", "lt"]).enabled_locales == [
        "fr",
        "lt",
    ]


def test_defaults_are_not_shared_between_instances() -> None:
    first = AppSettings()
    first.enabled_locales.append("xx")

    assert AppSettings().enabled_locales == list(DEFAULT_ENABLED_LOCALES)


@pytest.mark.parametrize("locales", [["fr"], ["da", "en"], list(SUPPORTED_LOCALES)])
def test_supported_locales_are_accepted(locales: list[str]) -> None:
    assert AppSettingsPatch(enabled_locales=locales).enabled_locales == locales


def test_unsupported_locales_are_refused() -> None:
    with pytest.raises(ValidationError, match="Unsupported locales: de, xx"):
        AppSettingsPatch(enabled_locales=["fr", "xx", "de"])


def test_enabling_no_locale_is_refused() -> None:
    # An empty list would leave the language menu empty and every visitor stuck
    # on whatever Paraglide falls back to.
    with pytest.raises(ValidationError, match="At least one locale"):
        AppSettingsPatch(enabled_locales=[])


def test_unsupported_default_locale_is_refused() -> None:
    with pytest.raises(ValidationError, match="Unsupported locale: xx"):
        AppSettingsPatch(default_locale="xx")


def test_locales_are_left_alone_when_the_patch_omits_them() -> None:
    patch = AppSettingsPatch(platform_name="Whatever")

    assert patch.enabled_locales is None
    assert patch.default_locale is None
    assert patch.model_dump(exclude_unset=True) == {"platform_name": "Whatever"}
