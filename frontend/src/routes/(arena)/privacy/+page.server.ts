import { api } from '$lib/fastapi-client'
import type { PublicLegalDocument } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import { logger } from '$lib/logger.server'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async ({ fetch }) => {
  try {
    return {
      privacyPolicy: await api.request<PublicLegalDocument>(
        `/settings/legal/privacy-policy?locale=${getLocale()}`,
        { fetch }
      )
    }
  } catch (error) {
    // Nothing published yet, or the backend is down: the page falls back to the
    // policy shipped with the frontend, but this is still logged so a backend
    // outage doesn't go unnoticed.
    logger.warn('Failed to load published privacy policy', { error: `${error}` })
    return { privacyPolicy: null }
  }
}
