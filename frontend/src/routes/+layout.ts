import { api } from '$lib/fastapi-client'
import type { APIData } from '$lib/models'

export async function load() {
  // Query votes depending on locale (sent as header)
  // Will return specific counter if locale is a country_portal else the default
  // Query votes depending on locale - only da or fr are valid for counter
  // const counterLocale = locale === 'da' ? 'da' : 'fr'
  // const votes = await api.get<VotesData>(`/counter?c=${counterLocale}`)
  const votes = await api.get<VotesData>(`/counter`)
  const data = await api.request<APIData>('/models/', { method: 'GET' })

  return { data, votes }
}
