import type { Locale } from '$lib/i18n/runtime'

export function formatRegion(code: string, locale: Locale) {
  const normalizedCode = code.trim().toUpperCase()
  const flag = /^[A-Z]{2}$/.test(normalizedCode)
    ? String.fromCodePoint(...[...normalizedCode].map((letter) => letter.charCodeAt(0) + 127397))
    : ''

  try {
    const name =
      new Intl.DisplayNames([locale], { type: 'region', fallback: 'code' }).of(normalizedCode) ??
      normalizedCode
    return { code: normalizedCode, flag, name }
  } catch {
    return { code: normalizedCode, flag, name: normalizedCode }
  }
}
