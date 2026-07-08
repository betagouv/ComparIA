import { api } from '$lib/fastapi-client'
import type { LayoutLoad } from './$types'

export const ssr = false // auth error on server side

export const load: LayoutLoad = async () => {
  // Unauthorized errors are handled globally, see hooks.client.ts
  // FIXME types
  const comparisons = await api.request<unknown>('/arena/comparison/list')

  return {
    comparisons
  }
}
