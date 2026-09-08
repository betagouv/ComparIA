from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from utils.database.models.app_settings import default_informational_legal_pages
from utils.database.settings import get_app_settings

INFORMATIONAL_PAGE_CONTENT_MAX_LENGTH = 200_000


class InformationalLegalPage(BaseModel):
    mode: Literal["internal", "external"] = "internal"
    external_url: str | None = None
    visible_in_legal_menu: bool = True
    visible_in_settings: bool = True
    content_by_locale: dict[str, str] = Field(default_factory=dict)

    @field_validator("external_url", mode="before")
    @classmethod
    def validate_external_url(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("External URL must be a string")
        url = value.strip()
        if not url:
            return None
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("External URL must be an absolute HTTPS URL")
        return url

    @field_validator("content_by_locale")
    @classmethod
    def validate_content(cls, value: dict[str, str]) -> dict[str, str]:
        for locale, content in value.items():
            if not locale or len(locale) > 16:
                raise ValueError(
                    "Content locale must contain between 1 and 16 characters"
                )
            if len(content) > INFORMATIONAL_PAGE_CONTENT_MAX_LENGTH:
                raise ValueError(
                    f"Content for {locale} must not exceed "
                    f"{INFORMATIONAL_PAGE_CONTENT_MAX_LENGTH} characters"
                )
        return value

    @model_validator(mode="after")
    def require_url_for_external_mode(self):
        if self.mode == "external" and self.external_url is None:
            raise ValueError("External URL is required in external mode")
        return self


class InformationalLegalPageCollection(BaseModel):
    legal_notice: InformationalLegalPage
    accessibility: InformationalLegalPage
    ecodesign: InformationalLegalPage


class InformationalLegalPages(BaseModel):
    pages: InformationalLegalPageCollection


def default_informational_pages() -> InformationalLegalPages:
    return InformationalLegalPages(
        pages=InformationalLegalPageCollection.model_validate(
            default_informational_legal_pages()
        )
    )


async def get_informational_legal_pages() -> InformationalLegalPages:
    settings = await get_app_settings()
    stored = settings.informational_legal_pages
    if not stored:
        return default_informational_pages()
    return InformationalLegalPages(
        pages=InformationalLegalPageCollection.model_validate(stored)
    )
