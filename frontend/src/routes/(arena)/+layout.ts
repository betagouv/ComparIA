import { queryComparisons } from '$lib/chatService.svelte'
import { api } from '$lib/fastapi-client'
import type { ToolPublic } from '$lib/generated/backend'
import {
  fallbackModes,
  fetchSelectionModes,
  type LoadedSelectionModes
} from '$lib/selectionModes.svelte'
import { parseCohortsParam } from '$lib/stores/cohortStore.svelte'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch, url, untrack }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  // Only the URL is known on the server, and the browser reads the same one
  // while hydrating, so both render the same menu. Cohorts kept in session
  // storage are caught up after mount, see initSelectionModesContext.
  const cohorts = parseCohortsParam(untrack(() => url.searchParams.get('c')))

  const [comparisons, tools, modes] = await Promise.all([
    queryComparisons(fetch, true),
    // Without the tools list the arena still works, only with no picker.
    api.request<ToolPublic[]>('/arena/tools', { fetch }).catch((error) => {
      console.error(`Unable to load tools: ${error.message}`)
      return [] as ToolPublic[]
    }),
    // Without the modes the arena still compares, with one blind draw.
    fetchSelectionModes(fetch, cohorts).catch((error) => {
      console.error(`Unable to load selection modes: ${error.message}`)
      return [] as LoadedSelectionModes['modes']
    })
  ])

  const toolKeys = tools.map((tool) => tool.key)
  const selectionModes: LoadedSelectionModes = modes.length
    ? { modes, cohorts, toolKeys, fallback: false }
    : { modes: fallbackModes(toolKeys), cohorts, toolKeys, fallback: true }

  return { ...data, comparisons, tools, selectionModes }
}
