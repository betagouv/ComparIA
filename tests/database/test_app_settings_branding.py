import asyncio
import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["LOG_FORMAT"] = "JSON"

from backend.admin.router import _to_app_settings_public
from backend.auth import router as auth_router
from utils.database.models.app_settings import (
    PRIMARY_COLOR_DARK_DEFAULT,
    PRIMARY_COLOR_LIGHT_DEFAULT,
    SECONDARY_COLOR_DARK_DEFAULT,
    SECONDARY_COLOR_LIGHT_DEFAULT,
    AppSettings,
    AppSettingsPatch,
)


def test_branding_defaults_match_the_accessible_light_and_dark_palette() -> None:
    settings = AppSettings()

    assert settings.primary_color_light == PRIMARY_COLOR_LIGHT_DEFAULT == "#6464F3"
    assert settings.primary_color_dark == PRIMARY_COLOR_DARK_DEFAULT == "#9898F8"
    assert settings.secondary_color_light == SECONDARY_COLOR_LIGHT_DEFAULT == "#FF9575"
    assert settings.secondary_color_dark == SECONDARY_COLOR_DARK_DEFAULT == "#FFCC00"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("primary_color_light", "#123456"),
        ("primary_color_dark", "#abcdef"),
        ("secondary_color_light", "#a1b2c3"),
        ("secondary_color_dark", "#a1b2c3"),
    ],
)
def test_color_patch_values_are_normalized_to_uppercase(
    field_name: str, value: str
) -> None:
    patch = AppSettingsPatch.model_validate({field_name: value})

    assert getattr(patch, field_name) == value.upper()


@pytest.mark.parametrize(
    "value",
    ["aabbcc", "#abcd", "#aabbccdd", "#gg0000", "#fff; color: red", ""],
)
def test_color_patch_values_must_use_strict_hex_format(value: str) -> None:
    with pytest.raises(ValidationError, match="#RRGGBB"):
        AppSettingsPatch(primary_color_light=value)


def test_color_patch_values_cannot_be_explicitly_null() -> None:
    with pytest.raises(ValidationError, match="cannot be null"):
        AppSettingsPatch.model_validate({"primary_color_light": None})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("primary_color_light", "#FFFFFF"),
        ("primary_color_dark", "#161616"),
    ],
)
def test_primary_colors_must_contrast_with_their_theme_background(
    field_name: str, value: str
) -> None:
    with pytest.raises(ValidationError, match="contrast ratio"):
        AppSettingsPatch.model_validate({field_name: value})


@pytest.mark.parametrize(
    "value", ["https://example.org", " https://example.org/path?q=1 "]
)
def test_homepage_url_accepts_absolute_https_urls(value: str) -> None:
    patch = AppSettingsPatch(homepage_url=value)

    assert patch.homepage_url == value.strip()


@pytest.mark.parametrize(
    "value",
    [
        "http://example.org",
        "/",
        "javascript:alert(1)",
        "data:text/html,hello",
        "file:///tmp/a",
        "https://user:password@example.org",
        "https://example.org/\njavascript:alert(1)",
    ],
)
def test_homepage_url_rejects_non_https_or_relative_urls(value: str) -> None:
    with pytest.raises(ValidationError, match="absolute HTTPS|whitespace"):
        AppSettingsPatch(homepage_url=value)


def test_empty_homepage_url_is_normalized_to_none() -> None:
    assert AppSettingsPatch(homepage_url="   ").homepage_url is None


def test_admin_settings_serialization_includes_branding_fields() -> None:
    row = AppSettings(
        primary_color_light="#112233",
        primary_color_dark="#223344",
        secondary_color_light="#334455",
        secondary_color_dark="#445566",
        homepage_url="https://example.org",
    )

    public = _to_app_settings_public(row)

    assert public.primary_color_light == "#112233"
    assert public.primary_color_dark == "#223344"
    assert public.secondary_color_light == "#334455"
    assert public.secondary_color_dark == "#445566"
    assert public.homepage_url == "https://example.org"


def test_public_auth_config_includes_branding_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = AppSettings(
        primary_color_light="#112233",
        primary_color_dark="#223344",
        secondary_color_light="#334455",
        secondary_color_dark="#445566",
        homepage_url="https://example.org",
    )

    async def get_settings() -> AppSettings:
        return row

    monkeypatch.setattr(auth_router, "get_app_settings", get_settings)

    config = asyncio.run(auth_router.get_config())

    assert config.primary_color_light == "#112233"
    assert config.primary_color_dark == "#223344"
    assert config.secondary_color_light == "#334455"
    assert config.secondary_color_dark == "#445566"
    assert config.homepage_url == "https://example.org"
