from typing import Annotated, Any, Generic, TypeVar
from urllib.parse import urlsplit

from pydantic import BeforeValidator, RootModel, ValidationInfo, model_validator

from utils.utils import SUPPORTED_LOCALES

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1"}


def strip_and_empty_as_none(v: str | None) -> str | None:
    v = v.strip() if v else None
    return None if not v else v


StripAndEmptyAsNone = BeforeValidator(strip_and_empty_as_none)

NonEmptyStr = Annotated[str, StripAndEmptyAsNone]


def is_secure_url(url: str) -> bool:
    """Whether `url` is https, or plain http on the local machine (the dev
    Keycloak). `hostname` is compared whole, so `localhost.evil.test` fails."""
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError:
        return False
    if parts.scheme == "https":
        return bool(hostname)
    return parts.scheme == "http" and hostname in _LOOPBACK_HOSTS


T = TypeVar("T")


class Translatable(RootModel[dict[str, T]], Generic[T]):
    @model_validator(mode="before")
    @classmethod
    def remove_empty(cls, data: Any):
        return {locale: value for locale, value in data.items() if value}

    @model_validator(mode="after")
    def check_locales(self, info: ValidationInfo):
        invalid_locales = set(self.root) - set(SUPPORTED_LOCALES)
        if invalid_locales:
            raise ValueError(f"Unsupported locale(s): {sorted(invalid_locales)}")

        return self

