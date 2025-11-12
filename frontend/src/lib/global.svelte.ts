import { env } from '$env/dynamic/public'
import { getLocale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'

const disabledLocaleCodes = env.PUBLIC_DISABLED_LOCALES
  ? env.PUBLIC_DISABLED_LOCALES.split(',').map((code) => code.trim())
  : null

type Locale = { code: string; short: string; long: string }

const ALL_LOCALES = [
  { code: 'da', short: 'DA', long: 'DA - Dansk' } as Locale,
  { code: 'fr', short: 'FR', long: 'FR - Français' } as Locale,
  { code: 'en', short: 'EN', long: 'EN - English' } as Locale,
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių' } as Locale,
  { code: 'sv', short: 'SV', long: 'SV - Svensk' } as Locale
] as const

export const LOCALES = ALL_LOCALES.filter((locale: Locale) => {
  return !disabledLocaleCodes?.includes(locale.code)
})

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}

export type I18nData = {
  contact: string
}

export function setI18nContext() {
  const i18nData: Record<string, I18nData> = {
    da: { contact: 'kontakt@ai-arenaen.dk' },
    fr: { contact: 'contact@comparia.beta.gouv.fr' }
  } as const
  const locale = getLocale() === 'da' ? 'da' : 'fr'
  setContext('i18n', i18nData[locale])
}

export function getI18nContext() {
  return getContext<I18nData>('i18n')
}
