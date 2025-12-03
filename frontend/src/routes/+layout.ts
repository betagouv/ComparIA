import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'
import { initializeCohortDetection } from '$lib/stores/cohortStore.svelte'

export async function load() {
  // Initialize cohort detection on first visit (client-side only)
  // This will only run once per browser session and provides reactive state
  if (typeof window !== 'undefined') {
    initializeCohortDetection()
  }

  // Get the current locale using the runtime function
  const locale = getLocale()

  // Query votes depending on locale - only da or fr are valid for counter
  const counterLocale = locale === 'da' ? 'da' : 'fr'
  const votes = await api.get<VotesData>(`/counter?c=${counterLocale}`)

  const data = await api.get<APIData>('/available_models')

  return { data, votes }
}
