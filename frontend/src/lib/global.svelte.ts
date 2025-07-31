import { api } from '$lib/api'
import { getLocale, setLocale, type Locale } from '$lib/i18n/runtime'

export type State = {
  loading: boolean
  locale: Locale
  votes?: { count: number; objective: number }
}

export const LOCALES = [
  { code: 'fr', short: 'FR', long: 'FR - Français' },
  { code: 'en', short: 'EN', long: 'EN - English' }
] as const

export const global = $state<State>({
  loading: false,
  locale: getLocale()
})

export function changeLocale(locale: Locale) {
  setLocale(locale)
  global.locale = locale
}

export function getVotes() {
  return api.get<State['votes']>('/counter').then((data) => {
    global.votes = data
  })
}
