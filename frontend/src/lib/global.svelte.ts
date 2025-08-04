import { getContext, setContext } from 'svelte'

export const LOCALES = [
  { code: 'fr', short: 'FR', long: 'FR - Français' },
  { code: 'en', short: 'EN', long: 'EN - English' },
  { code: 'lt', short: 'LT', long: 'LT - Lietuvių' },
  { code: 'se', short: 'SE', long: 'SE - Svensk' }
] as const

export type VotesData = { count: number; objective: number }

export function setVotesContext(votes: VotesData) {
  setContext('votes', votes)
}

export function getVotesContext() {
  return getContext<VotesData>('votes')
}
