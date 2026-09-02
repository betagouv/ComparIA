import type { AuthConfig, AuthUser } from '$lib/auth.svelte'
import { api } from '$lib/fastapi-client'
import type { LLMList } from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'

export async function load({ fetch }) {
  const votes = await api.request<VotesData>('/counter', { fetch })
  const data = await api.request<LLMList>('/models/', { fetch })
  const authConfig = await api.request<AuthConfig>('/auth/config', { fetch })
  const auth = await api.request<{ user: AuthUser | null }>('/auth/me', { fetch })

  return { data, votes, auth: { user: auth.user, config: authConfig } }
}
