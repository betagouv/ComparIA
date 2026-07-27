// This page and its privacy policy sibling sit outside src/routes/arene on
// purpose: they are public documents, so they keep the public layout and stay
// clear of the arena layout load, which needs a session.
import { api } from '$lib/fastapi-client'
import type { PublicLegalDocument } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async ({ fetch }) => {
  try {
    return {
      terms: await api.request<PublicLegalDocument>(`/settings/legal/terms?locale=${getLocale()}`, {
        fetch
      })
    }
  } catch {
    // Nothing published yet, or the backend is down: the page says so instead of erroring.
    return { terms: null }
  }
}
