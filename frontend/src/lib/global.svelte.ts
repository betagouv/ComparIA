import { getLocale, type Locale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'

export type LocaleOption = { code: Locale; short: string; long: string }

// Every locale the bundle ships with. Which of them an instance offers is an
// admin setting (AppSettings.enabled_locales), not a property of the domain:
// picking a language never moves you to another instance.
export const ALL_LOCALES = [
  { code: 'da', short: 'DA', long: 'DA - Dansk' },
  { code: 'fr', short: 'FR', long: 'FR - Français' },
  { code: 'en', short: 'EN', long: 'EN - English' },
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių' },
  { code: 'sv', short: 'SV', long: 'SV - Svensk' }
] satisfies LocaleOption[]

// Falls back to the full list so a frontend deployed ahead of its backend still
// renders a language menu instead of throwing on a missing field.
export function getLocales(enabledLocales: string[] | undefined): LocaleOption[] {
  if (!enabledLocales?.length) return ALL_LOCALES
  return ALL_LOCALES.filter((locale) => enabledLocales.includes(locale.code))
}

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}

export type I18nData = {
  contact: string
  peopleUsingAIDataLink: string
}

export function setI18nContext() {
  const i18nData: Record<string, I18nData> = {
    da: {
      contact: 'kontakt@ai-arenaen.dk',
      peopleUsingAIDataLink:
        'https://ec.europa.eu/eurostat/fr/web/products-eurostat-news/w/ddn-20251216-3'
    },
    fr: {
      contact: 'contact@comparia.beta.gouv.fr',
      peopleUsingAIDataLink:
        'https://www.credoc.fr/publications/barometre-du-numerique-2026-rapport'
    }
  } as const
  const locale = getLocale() === 'da' ? 'da' : 'fr'
  setContext('i18n', i18nData[locale])
}

export function getI18nContext() {
  return getContext<I18nData>('i18n')
}
