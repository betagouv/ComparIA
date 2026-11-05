from collections.abc import Collection
from typing import Annotated, cast

from fastapi import Depends

from utils.database.settings import get_app_settings
from utils.i18n import DEFAULT_LOCALE, SupportedLocale


async def get_safe_locale(locale: str | None = None) -> SupportedLocale:
    """
    Safely get an enabled locale.
    Fallback to db's default locale if given locale not in enabled.
    """
    settings = await get_app_settings()
    if locale and locale in settings.enabled_locales:
        return cast(SupportedLocale, locale)
    return settings.default_locale


LocaleQuery = Annotated[SupportedLocale, Depends(get_safe_locale)]


def pick_locale(locale: str | None, available: Collection[str]) -> str:
    """The closest locale we have copy for: exact, then same language, then
    the base locale everything is written in first."""
    if locale:
        if locale in available:
            return locale
        language = locale.split("-")[0]
        if language in available:
            return language
    return DEFAULT_LOCALE
