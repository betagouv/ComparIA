import { api } from '$lib/fastapi-client'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'

export async function load() {
  // Query votes depending on locale
  // Will return specific counter if locale is a country_portal else the default
  const votes = await api.request<VotesData>(`/counter?country_portal=${getLocale()}`, {
    method: 'GET'
  })

  const data = await api.request<APIData>('/models', { method: 'GET' })

  return { data, votes }
}
