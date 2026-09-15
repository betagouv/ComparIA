from collections.abc import Collection

BASE_LOCALE = "fr"


def pick_locale(locale: str | None, available: Collection[str]) -> str:
    """The closest locale we have copy for: exact, then same language, then
    the base locale everything is written in first."""
    if locale:
        if locale in available:
            return locale
        language = locale.split("-")[0]
        if language in available:
            return language
    return BASE_LOCALE
