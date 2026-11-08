from typing import Literal, TypeVar, get_args

# Locales compiled into the frontend bundle, see frontend/comparia.inlang/settings.json.
# An instance enables a subset of these. Anything outside the tuple is refused
# rather than stored, because the frontend has no messages for it and would fall
# back to the base locale without telling anyone.
SupportedLocale = Literal["da", "en", "fr", "it", "lt", "nb-NO", "sv"]
SUPPORTED_LOCALES: tuple[SupportedLocale, ...] = get_args(SupportedLocale)

# Hard default locale, mainly used for internal code:
# - define the main project language (for weblate, to remove stale keys in i18n cli command, etc.)
# - default locale for `settings.COMPARIA_INSTANCE_NAME` and therefore `AppSettings.default_locale`
DEFAULT_LOCALE: SupportedLocale = "en"

# What a new instance starts with, and what the migration backfills onto the
# existing ones. Narrower than SUPPORTED_LOCALES: it, lt, nb-NO and sv ship too
# few translated messages to be offered unasked, which is why prod carried
# PUBLIC_DISABLED_LOCALES="lt,sv". An admin can still turn them on from
# /admin/locales, which is the point of the setting.
DEFAULT_ENABLED_LOCALES: tuple[SupportedLocale, ...] = ("da", "en", "fr")

T = TypeVar("T")
TranslatableRaw = dict[SupportedLocale, T]
