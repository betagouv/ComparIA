import type { Locale } from '$lib/i18n/runtime'

/** The name of a language, written in the language the reader uses. */
export function formatLanguage(code: string, locale: Locale) {
  try {
    return new Intl.DisplayNames([locale], { type: 'language', fallback: 'code' }).of(code) ?? code
  } catch {
    return code
  }
}
