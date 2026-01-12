import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'

export async function load() {
  // Query votes depending on locale
  // Will return specific counter if locale is a country_portal else the default
  const votes = await api.get<VotesData>(`/counter?country_portal=${getLocale()}`)

  const data = await api.get<APIData>('/models')

  return { data, votes }
}
