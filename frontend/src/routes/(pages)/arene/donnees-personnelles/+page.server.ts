import { api } from '$lib/fastapi-client'
import type { PublicLegalDocument } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async ({ fetch }) => {
  try {
    return {
      privacyPolicy: await api.request<PublicLegalDocument>(
        `/settings/legal/privacy-policy?locale=${getLocale()}`,
        { fetch }
      )
    }
  } catch {
    // Nothing published yet, or the backend is down: the page falls back to the
    // policy shipped with the frontend.
    return { privacyPolicy: null }
  }
}
