import { api } from '$lib/fastapi-client'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'

export async function load() {
  // Query votes depending on locale (sent as header)
  // Will return specific counter if locale is a country_portal else the default
  // Query votes depending on locale - only da or fr are valid for counter
  const counterLocale = getLocale() === 'da' ? 'da' : 'fr'
  const votes = await api.request<VotesData>(`/counter?c=${counterLocale}`, { method: 'GET' })
  const data = await api.request<APIData>('/models/', { method: 'GET' })

  return { data, votes }
}
