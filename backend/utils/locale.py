from collections.abc import Collection
from typing import Annotated, cast

from fastapi import Depends, HTTPException, status

from utils.database.settings import get_app_settings
from utils.i18n import DEFAULT_LOCALE, SupportedLocale


async def get_safe_locale(locale: SupportedLocale | None = None) -> SupportedLocale:
    """
    Safely get an enabled locale.
    Fallback to db's default locale if given locale not in enabled.
    """
    settings = await get_app_settings()
    if locale and locale in settings.enabled_locales:
        return cast(SupportedLocale, locale)
    return settings.default_locale


async def get_strict_locale(locale: SupportedLocale) -> SupportedLocale:
    """
    Get an enabled locale or error out.
    """
    settings = await get_app_settings()
    if locale not in settings.enabled_locales:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unsupported locale '{locale}'."
        )
    return locale


LocaleQuery = Annotated[SupportedLocale, Depends(get_safe_locale)]
LocaleQueryStrict = Annotated[SupportedLocale, Depends(get_strict_locale)]


def pick_locale(
    locale: SupportedLocale | None,
    available: Collection[str],
) -> SupportedLocale:
    """The closest locale we have copy for: exact, then same language, then
    the base locale everything is written in first."""
    if locale:
        if locale in available:
            return locale
        language = locale.split("-")[0]
        if language in available:
            return language
    return DEFAULT_LOCALE
