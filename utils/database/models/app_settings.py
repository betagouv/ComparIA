import uuid
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import ValidationInfo, field_validator
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime

PRIMARY_COLOR_LIGHT_DEFAULT = "#6464F3"
PRIMARY_COLOR_DARK_DEFAULT = "#9898F8"
SECONDARY_COLOR_LIGHT_DEFAULT = "#FF9575"
SECONDARY_COLOR_DARK_DEFAULT = "#FFCC00"

_HEX_COLOR_LENGTH = 7
_HOMEPAGE_URL_MAX_LENGTH = 2_048


def _normalize_hex_color(value: object) -> str:
    if not isinstance(value, str) or len(value) != _HEX_COLOR_LENGTH:
        raise ValueError("Color must use the #RRGGBB format")
    if value[0] != "#" or any(
        char not in "0123456789abcdefABCDEF" for char in value[1:]
    ):
        raise ValueError("Color must use the #RRGGBB format")
    return value.upper()


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    red, green, blue = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _normalize_homepage_url(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Homepage URL must be a string")

    url = value.strip()
    if not url:
        return None
    if len(url) > _HOMEPAGE_URL_MAX_LENGTH:
        raise ValueError("Homepage URL must not exceed 2048 characters")
    if any(character.isspace() or ord(character) < 32 for character in url):
        raise ValueError(
            "Homepage URL must not contain whitespace or control characters"
        )

    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Homepage URL must be an absolute HTTPS URL")
    return url


# Locales compiled into the frontend bundle, see frontend/comparia.inlang/settings.json.
# An instance enables a subset of these. Anything outside the tuple is refused
# rather than stored, because the frontend has no messages for it and would fall
# back to the base locale without telling anyone.
SUPPORTED_LOCALES = ("da", "en", "fr", "lt", "sv")


def _check_enabled_locales(value: list[str]) -> list[str]:
    if not value:
        raise ValueError("At least one locale must be enabled")
    unknown = sorted(set(value) - set(SUPPORTED_LOCALES))
    if unknown:
        raise ValueError(f"Unsupported locales: {', '.join(unknown)}")
    return value


class AppSettings(SQLModel, table=True):
    """Singleton row (id=1) holding product settings editable from the admin panel."""

    __tablename__ = "app_settings"

    id: int = Field(default=1, primary_key=True)
    auth_access_policy: str = Field(default="anonymous_first")
    auth_domain_allowlist: Annotated[list[str], Field(sa_type=JSONB)] = []
    votes_objective: int = Field(default=300_000)
    platform_name: str = Field(default="Compar:IA")
    legal_presentation: Annotated[dict | None, Field(sa_type=JSONB)] = None
    primary_color_light: str = Field(default=PRIMARY_COLOR_LIGHT_DEFAULT, max_length=7)
    primary_color_dark: str = Field(default=PRIMARY_COLOR_DARK_DEFAULT, max_length=7)
    secondary_color_light: str = Field(
        default=SECONDARY_COLOR_LIGHT_DEFAULT, max_length=7
    )
    secondary_color_dark: str = Field(
        default=SECONDARY_COLOR_DARK_DEFAULT, max_length=7
    )
    homepage_url: str | None = Field(default=None, max_length=_HOMEPAGE_URL_MAX_LENGTH)
    logo: Annotated[bytes | None, Field(sa_type=LargeBinary)] = None
    logo_content_type: str | None = None
    enabled_locales: Annotated[list[str], Field(sa_type=JSONB)] = list(
        SUPPORTED_LOCALES
    )
    default_locale: str = Field(default="fr")
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")


class AppSettingsPublic(SQLModel):
    auth_access_policy: Literal["anonymous_first", "sign_in_required"]
    auth_domain_allowlist: list[str]
    votes_objective: int
    platform_name: str
    primary_color_light: str
    primary_color_dark: str
    secondary_color_light: str
    secondary_color_dark: str
    homepage_url: str | None
    has_custom_logo: bool
    enabled_locales: list[str]
    default_locale: str
    updated_at: str
    updated_by: uuid.UUID | None = None


class AppSettingsPatch(SQLModel):
    auth_access_policy: Literal["anonymous_first", "sign_in_required"] | None = None
    auth_domain_allowlist: list[str] | None = None
    votes_objective: int | None = None
    platform_name: str | None = None
    primary_color_light: str | None = None
    primary_color_dark: str | None = None
    secondary_color_light: str | None = None
    secondary_color_dark: str | None = None
    homepage_url: str | None = Field(default=None, max_length=_HOMEPAGE_URL_MAX_LENGTH)
    enabled_locales: list[str] | None = None
    default_locale: str | None = None

    @field_validator(
        "primary_color_light",
        "primary_color_dark",
        "secondary_color_light",
        "secondary_color_dark",
        mode="before",
    )
    @classmethod
    def normalize_colors(cls, value: object, info: ValidationInfo) -> str:
        if value is None:
            raise ValueError("Color cannot be null")
        color = _normalize_hex_color(value)
        if info.field_name == "primary_color_light":
            background = "#FFFFFF"
        elif info.field_name == "primary_color_dark":
            background = "#161616"
        else:
            return color
        if _contrast_ratio(color, background) < 4.5:
            raise ValueError(
                "Primary color must have a contrast ratio of at least 4.5:1 "
                "against the theme background"
            )
        return color

    @field_validator("homepage_url", mode="before")
    @classmethod
    def normalize_homepage_url(cls, value: object) -> str | None:
        return _normalize_homepage_url(value)

    @field_validator("enabled_locales")
    @classmethod
    def validate_enabled_locales(cls, value: list[str] | None) -> list[str] | None:
        return value if value is None else _check_enabled_locales(value)

    @field_validator("default_locale")
    @classmethod
    def validate_default_locale(cls, value: str | None) -> str | None:
        if value is not None and value not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported locale: {value}")
        return value
