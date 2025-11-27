import { api } from '$lib/api'
import { initializeCohortDetection } from '$lib/stores/cohortStore'
import type { VotesData } from '$lib/global.svelte'
import type { APIData } from '$lib/models'

export async function load() {


  // Initialize cohort detection on first visit (client-side only)
  // This will only run once per browser session and provides reactive state
  if (typeof window !== 'undefined') {
    initializeCohortDetection()
  }



  // FIXME query votes depending on locale
  const votes = await api.get<VotesData>('/counter')
  const data = await api.get<APIData>('/available_models')

  return { data, votes }
}
