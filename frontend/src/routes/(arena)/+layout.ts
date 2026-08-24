import { queryComparisons } from '$lib/chatService.svelte'
import { api } from '$lib/fastapi-client'
import type { ToolPublic } from '$lib/generated/backend'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  return {
    ...data,
    comparisons: await queryComparisons(fetch),
    // An instance with no tools configured simply shows no picker.
    tools: await api.request<ToolPublic[]>('/arena/tools').catch(() => [] as ToolPublic[])
  }
}
