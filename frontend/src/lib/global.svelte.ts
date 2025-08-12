import { getContext, setContext } from 'svelte'

export const LOCALES = [
  { code: 'da', short: 'DA', long: 'DA - Dansk'},
  { code: 'en', short: 'EN', long: 'EN - English' },
  { code: 'fr', short: 'FR', long: 'FR - Français' },
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių' },
  { code: 'sv', short: 'SV', long: 'SV - Svensk' }
] as const

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}
