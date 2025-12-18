import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'

export async function load() {
  // Get the current locale using the runtime function
  const locale = getLocale()

  // Query votes depending on locale - only da or fr are valid for counter
  const counterLocale = locale === 'da' ? 'da' : 'fr'
  const votes = await api.get<VotesData>(`/counter?c=${counterLocale}`)

  const data = await api.get<APIData>('/models')

  return { data, votes }
}
