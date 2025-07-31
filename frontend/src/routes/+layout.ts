import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import type { APIBotModel } from '$lib/models'

export async function load() {
  const votes = await api.get<VotesData>('/counter')
  const models = await api.get<APIBotModel[]>('/available_models')

  return { models, votes }
}
