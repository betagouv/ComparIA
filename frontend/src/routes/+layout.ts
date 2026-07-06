import { api } from '$lib/fastapi-client'
import type { LLMList } from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'

export async function load() {
  const votes = await api.request<VotesData>('/counter')
  const data = await api.request<LLMList>('/models/')

  return { data, votes }
}
