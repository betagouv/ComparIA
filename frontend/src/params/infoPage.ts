import type { ParamMatcher } from '@sveltejs/kit'

export const match: ParamMatcher = (param: unknown) => {
  if (param !== 'legal_notice' && param !== 'accessibility' && param !== 'ecodesign') return false
  return true
}
