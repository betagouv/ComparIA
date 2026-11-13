import pytest

from backend.utils.locale import LocalesSettings, pick_locale, pick_translation
from utils.i18n import TranslatableRaw

COPY: TranslatableRaw[str] = {"fr": "Bonjour", "en": "Hello", "da": "Hej"}
ONLY_DA: TranslatableRaw[str] = {"da": "Hej"}


def test_exact_enabled_locale():
    locales = LocalesSettings(default="fr", enabled=["fr", "en", "da"])
    assert pick_translation(COPY, "da", locales) == ("da", "Hej")


def test_instance_default_when_locale_has_no_copy():
    locales = LocalesSettings(default="da", enabled=["sv", "da"])
    assert pick_locale(COPY, "sv", locales) == "da"


def test_first_enabled_locale_in_enabled_order():
    locales = LocalesSettings(default="sv", enabled=["sv", "da", "fr"])
    for _ in range(20):
        assert pick_locale(COPY, "sv", locales) == "da"


def test_falls_back_to_hard_default_when_no_enabled_locale_has_copy():
    locales = LocalesSettings(default="sv", enabled=["sv"])
    assert pick_translation(COPY, "sv", locales) == ("en", "Hello")


def test_falls_back_to_any_copy_when_no_enabled_nor_default_copy():
    locales = LocalesSettings(default="sv", enabled=["sv"])
    assert pick_translation(ONLY_DA, "sv", locales) == ("da", "Hej")


def test_empty_contents_raise():
    locales = LocalesSettings(default="fr", enabled=["fr"])
    with pytest.raises(ValueError):
        pick_locale({}, "fr", locales)
