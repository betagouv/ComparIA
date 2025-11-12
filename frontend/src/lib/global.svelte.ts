import { dev } from '$app/environment'
import { env } from '$env/dynamic/public'
import { getLocale, type Locale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'

const disabledLocaleCodes = env.PUBLIC_DISABLED_LOCALES
  ? env.PUBLIC_DISABLED_LOCALES.split(',').map((code) => code.trim())
  : null

export type LocaleOption = { code: Locale; short: string; long: string; host: string }

const ALL_LOCALES = [
  { code: 'da', short: 'DA', long: 'DA - Dansk', host: dev ? 'localhost:5173' : 'ai-arenaen.dk' },
  {
    code: 'fr',
    short: 'FR',
    long: 'FR - Français',
    host: dev ? 'localhost:5173' : 'comparia.beta.gouv.fr'
  },
  {
    code: 'en',
    short: 'EN',
    long: 'EN - English',
    host: dev ? 'localhost:5173' : 'comparia.beta.gouv.fr'
  },
  {
    code: 'lt',
    short: 'LT',
    long: 'LT - Lietuvių',
    host: dev ? 'localhost:5173' : 'comparia.beta.gouv.fr'
  },
  {
    code: 'sv',
    short: 'SV',
    long: 'SV - Svensk',
    host: dev ? 'localhost:5173' : 'comparia.beta.gouv.fr'
  }
] satisfies LocaleOption[]

export const LOCALES = ALL_LOCALES.filter((locale) => {
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
