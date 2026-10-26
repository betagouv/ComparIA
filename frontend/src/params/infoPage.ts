import { INFORMATIONAL_PAGE_KEYS, type InformationalPageKeys } from '$lib/generated/constants'
import type { ParamMatcher } from '@sveltejs/kit'

export const match: ParamMatcher = (param: unknown) => {
  return INFORMATIONAL_PAGE_KEYS.includes(param as InformationalPageKeys)
}
