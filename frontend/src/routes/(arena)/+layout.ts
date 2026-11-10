import { queryComparisons } from '$lib/chatService.svelte'
import { api } from '$lib/fastapi-client'
import type { ToolPublic } from '$lib/generated/backend'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  const [comparisons, tools] = await Promise.all([
    queryComparisons(fetch, true),
    // Without the tools list the arena still works, only with no picker.
    api.request<ToolPublic[]>('/arena/tools', { fetch }).catch((error) => {
      console.error(`Unable to load tools: ${error.message}`)
      return [] as ToolPublic[]
    })
  ])

  return { ...data, comparisons, tools }
}
