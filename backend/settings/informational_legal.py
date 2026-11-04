from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from backend.utils.locale import pick_locale
from utils.database.settings import get_app_settings
from utils.validation import NonEmptyStr, Translatable

LegalPageKey = Literal["legal_notice", "accessibility", "ecodesign"]


class InformationalLegalPageLink(BaseModel):
    mode: Literal["internal", "external"] = "internal"
    external_url: Annotated[NonEmptyStr | None, Field(validate_default=True)] = None
    visible_in_legal_menu: bool = True
    visible_in_settings: bool = True

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

    @field_validator("external_url", mode="after")
    @classmethod
    def require_url_for_external_mode(
        cls, value: str | None, info: ValidationInfo
    ) -> str:
        if info.data["mode"] == "external" and value is None:
            raise ValueError("External URL is required in external mode")
        return value


class InformationalLegalPage(InformationalLegalPageLink, extra="forbid"):
    content_by_locale: Translatable[
        Annotated[str, Field(min_length=1, max_length=200_000)]
    ] = Field(default_factory=dict)


InformationalLegalPageAnno = Annotated[
    InformationalLegalPage, Field(default_factory=InformationalLegalPage)
]


class InformationalLegalPages(BaseModel, extra="forbid"):
    legal_notice: InformationalLegalPageAnno
    accessibility: InformationalLegalPageAnno
    ecodesign: InformationalLegalPageAnno


async def get_informational_legal_pages() -> InformationalLegalPages:
    settings = await get_app_settings()
    stored = settings.informational_legal_pages
    if not stored:
        return InformationalLegalPages()
    return InformationalLegalPages.model_validate(stored)


async def get_informational_legal_page(
    key: LegalPageKey,
) -> InformationalLegalPage | None:
    pages = await get_informational_legal_pages()
    return getattr(pages, key)


class InformationalLegalPageContent(BaseModel):
    content: str
    locale: str


async def get_informational_legal_page_content(
    key: LegalPageKey, locale: str
) -> InformationalLegalPageContent | None:
    page = await get_informational_legal_page(key)
    contents = page.content_by_locale.root
    available_locale = pick_locale(locale, contents)

    if page.mode == "external" or not available_locale in contents:
        return None

    return InformationalLegalPageContent(
        content=contents[available_locale],
        locale=available_locale,
    )


InformationalLegalPageLinkAnno = Annotated[
    InformationalLegalPageLink,
    Field(default_factory=InformationalLegalPageLink),
]


class InformationalLegalPageLinks(BaseModel, extra="forbid"):
    legal_notice: InformationalLegalPageLinkAnno
    accessibility: InformationalLegalPageLinkAnno
    ecodesign: InformationalLegalPageLinkAnno


async def get_informational_legal_pages_links() -> InformationalLegalPageLinks:
    settings = await get_app_settings()
    stored = settings.informational_legal_pages
    if not stored:
        return InformationalLegalPageLinks()
    return InformationalLegalPageLinks.model_validate(stored)
