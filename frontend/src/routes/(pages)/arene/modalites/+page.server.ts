// This page and its privacy policy sibling sit outside src/routes/arene on
// purpose: they are public documents, so they keep the public layout and stay
// clear of the arena layout load, which needs a session.
import { api } from '$lib/fastapi-client'
import type { PublicLegalDocument } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import { logger } from '$lib/logger.server'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async ({ fetch }) => {
  try {
    return {
      terms: await api.request<PublicLegalDocument>(`/settings/legal/terms?locale=${getLocale()}`, {
        fetch
      })
    }
  } catch (error) {
    // Nothing published yet, or the backend is down: the page says so instead of
    // erroring, but this is still logged since a fresh install should have a
    // seeded document and a persistent failure here needs attention.
    logger.warn('Failed to load published terms', { error: `${error}` })
    return { terms: null }
  }
}
