import { api } from '$lib/fastapi-client'
import type { LLMList } from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'

export async function load({ fetch }) {
  const votes = await api.request<VotesData>('/counter', { fetch })
  const data = await api.request<LLMList>('/models/', { fetch })

  return { data, votes }
}
