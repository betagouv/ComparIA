import { queryComparisons } from '$lib/chatService.svelte'
import { api } from '$lib/fastapi-client'
import type { ToolPublic } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  const [comparisons, tools] = await Promise.all([
    queryComparisons(fetch, true),
    // Without the tools list the arena still works, only with no picker.
    api
      .request<ToolPublic[]>('/tools', { fetch, searchParams: { locale: getLocale() } })
      .catch((error) => {
        console.error(`Unable to load tools: ${error.message}`)
        return [] as ToolPublic[]
      })
  ])

  return { ...data, comparisons, tools }
}
