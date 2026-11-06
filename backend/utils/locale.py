from dataclasses import dataclass
from typing import Annotated, TypeVar, cast

from fastapi import Depends, HTTPException, status

from utils.database.settings import get_app_settings
from utils.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, SupportedLocale


@dataclass
class LocalesSettings:
    default: SupportedLocale
    enabled: list[SupportedLocale]


DEFAULT_LOCALES_SETTINGS = LocalesSettings(
    default=DEFAULT_LOCALE, enabled=list(SUPPORTED_LOCALES)
)


async def get_locales_settings() -> LocalesSettings:
    """
    Helper to easy get default and enabled locales from settings.
    """
    settings = await get_app_settings()
    return LocalesSettings(
        default=settings.default_locale, enabled=settings.enabled_locales
    )


async def get_safe_locale(locale: SupportedLocale | None = None) -> SupportedLocale:
    """
    Safely get an enabled locale.
    Fallback to db's default locale if given locale not in enabled.
    """
    locales = await get_locales_settings()
    if locale and locale in locales.enabled:
        return cast(SupportedLocale, locale)
    return locales.default


async def get_strict_locale(locale: SupportedLocale) -> SupportedLocale:
    """
    Get an enabled locale or error out.
    """
    locales = await get_locales_settings()
    if locale not in locales.enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unsupported locale '{locale}'."
        )
    return locale


LocaleQuery = Annotated[SupportedLocale, Depends(get_safe_locale)]
LocaleQueryStrict = Annotated[SupportedLocale, Depends(get_strict_locale)]


T = TypeVar("T")


def pick_locale(
    contents: dict[SupportedLocale, T],
    locale: SupportedLocale | None,
    locales: LocalesSettings = DEFAULT_LOCALES_SETTINGS,
) -> SupportedLocale:
    """
    The closest locale we have copy for: exact, then same language, then the default
    locale and finally the first available locale in enabled ones.
    """
    available_locales = list(set(contents.keys()).intersection(set(locales.enabled)))
    tries = [locale, locales.default, *available_locales]

    for l in tries:
        if not l:
            continue
        if l in available_locales:
            return cast(SupportedLocale, l)
        l_ = l.split("-")[0]
        if l_ in available_locales:
            return cast(SupportedLocale, l_)

    raise ValueError("Couldn't find any enabled locale in available content.")


def pick_translation(
    contents: dict[SupportedLocale, T],
    locale: SupportedLocale | None,
    locales: LocalesSettings = DEFAULT_LOCALES_SETTINGS,
) -> tuple[SupportedLocale, T]:
    """
    The closest locale and content we have copy for: exact, then same language,
    then the default locale and finally the first available locale in enabled ones.
    """
    available_locale = pick_locale(contents, locale, locales)
    return available_locale, contents[available_locale]
