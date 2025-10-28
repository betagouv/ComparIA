import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import type { APIData } from '$lib/models'

export async function load() {
  // FIXME query votes depending on locale
  const votes = await api.get<VotesData>('/counter')
  const data = await api.get<APIData>('/available_models')

  return { data, votes }
}
