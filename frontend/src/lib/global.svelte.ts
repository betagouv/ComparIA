import { browser } from '$app/environment'
import { getLocale, setLocale, type Locale } from '$lib/i18n/runtime'
import { getContext, setContext } from 'svelte'

export type State = {
  loading: boolean
  locale?: Locale
}

export const LOCALES = [
  { code: 'fr', short: 'FR', long: 'FR - Français' },
  { code: 'en', short: 'EN', long: 'EN - English' },
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių' },
  { code: 'se', short: 'SE', long: 'SE - Svensk' }
] as const

export const global = $state<State>({
  loading: false,
  // FIXME on server side the locale is taken from preferredLanguage which is weird
  locale: browser ? getLocale() : undefined
})

export function changeLocale(locale: Locale) {
  setLocale(locale)
  global.locale = locale
}

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}
