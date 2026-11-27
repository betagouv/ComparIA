import { api } from '$lib/fastapi-client'
import type { PublicLegalDocument } from '$lib/generated/backend'
import type { LegalDocumentKeys } from '$lib/generated/constants'
import { getLocale } from '$lib/i18n/runtime'
import { logger } from '$lib/logger.server'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async ({ params, fetch }) => {
  const legalDocKey = params.legalDoc as LegalDocumentKeys

  try {
    return {
      doc: await api.request<PublicLegalDocument>(`/settings/legal/${legalDocKey}`, {
        fetch,
        searchParams: { locale: getLocale() }
      })
    }
  } catch (error) {
    // Nothing published yet, or the backend is down: the page says so instead of erroring
    logger.warn(`Failed to load published ${legalDocKey}`, { error: `${error}` })
    return { doc: null }
  }
}
