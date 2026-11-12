import { getLocale, locales, setLocale, type Locale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'
import { getAuthContext } from './authContext.svelte'

export type LocaleDesc = { short: string; long: string }

// Every locale the bundle ships with. Which of them an instance offers is an
// admin setting (AppSettings.enabled_locales), not a property of the domain:
// picking a language never moves you to another instance.
export const ALL_LOCALES: Record<Locale, LocaleDesc> = {
  da: { short: 'DA', long: 'DA - Dansk' },
  fr: { short: 'FR', long: 'FR - Français' },
  en: { short: 'EN', long: 'EN - English' },
  it: { short: 'IT', long: 'IT - Italiano' },
  lt: { short: 'LT', long: 'LT - Lietuvių' },
  'nb-NO': { short: 'NB', long: 'NB - Norsk bokmål' },
  sv: { short: 'SV', long: 'SV - Svensk' }
}

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}

export function getLocalesContext() {
  // Query current locale only once, on change a page reload occurs
  const currentLocale = getLocale()
  const auth = getAuthContext()
  const defaultLocale = $derived(auth.config.default_locale)
  const allLocales = $derived(sortLocales(locales))
  const enabledLocales = $derived(sortLocales(auth.config.enabled_locales))
  const enabledOptions = $derived(asOptions(enabledLocales))
  const allOptions = $derived(asOptions(locales))

  function getLabel(locale: Locale, variant: 'long' | 'short' = 'long') {
    return ALL_LOCALES[locale][variant]
  }

  function asOptions(locales: Readonly<Locale[]>, variant: 'long' | 'short' = 'long') {
    return locales.map((value) => ({ value, label: getLabel(value, variant) }))
  }

  function sortLocales(locales: Readonly<Locale[]>) {
    // Put default locale in first position
    return [...locales].sort(
      (left, right) => Number(right === defaultLocale) - Number(left === defaultLocale)
    )
  }

  return {
    get current() {
      return currentLocale
    },
    set current(value: Locale) {
      setLocale(value)
    },
    get default() {
      return defaultLocale
    },
    get enabled() {
      return enabledLocales
    },
    get enabledOptions() {
      return enabledOptions
    },
    get all() {
      return allLocales
    },
    get allOptions() {
      return allOptions
    },
    getLabel,
    asOptions
  }
}
