import type { ParamMatcher } from '@sveltejs/kit'

export const match: ParamMatcher = (param: unknown) => {
  if (param !== 'terms' && param !== 'privacy_policy') return false
  return true
}
