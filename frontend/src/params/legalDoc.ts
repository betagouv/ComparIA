import { LEGAL_DOCUMENT_KEYS, type LegalDocumentKeys } from '$lib/generated/constants'
import type { ParamMatcher } from '@sveltejs/kit'

export const match: ParamMatcher = (param: unknown) => {
  return LEGAL_DOCUMENT_KEYS.includes(param as LegalDocumentKeys)
}
