import { queryComparisons } from '$lib/chatService.svelte'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  return {
    ...data,
    comparisons: await queryComparisons(fetch)
  }
}
