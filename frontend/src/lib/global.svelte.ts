import { dev } from '$app/environment'
import { getLocale, type Locale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'

export type LocaleOption = { code: Locale; short: string; long: string; host: string }

const DEFAULT_HOST = dev ? 'localhost:5173' : 'comparia.beta.gouv.fr'
export const HOST_TO_LOCALE = dev
  ? {
      '127.0.0.1:8080': 'da'
    }
  : {
      'ai-arenaen.dk': 'da',
      'aiarenaen.dk': 'da'
    }
export const ALL_LOCALES = [
  { code: 'da', short: 'DA', long: 'DA - Dansk', host: dev ? '127.0.0.1:8080' : 'ai-arenaen.dk' },
  { code: 'fr', short: 'FR', long: 'FR - Français', host: DEFAULT_HOST },
  { code: 'en', short: 'EN', long: 'EN - English', host: DEFAULT_HOST },
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių', host: DEFAULT_HOST },
  { code: 'sv', short: 'SV', long: 'SV - Svensk', host: DEFAULT_HOST }
] satisfies LocaleOption[]

// enabledLocales comes from AppSettings (admin-editable, see auth.config),
// replacing the old build-time PUBLIC_DISABLED_LOCALES env var.
export function getLocales(enabledLocales: string[]): LocaleOption[] {
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
