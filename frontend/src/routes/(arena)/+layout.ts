import { browser } from '$app/environment'
import { queryComparisons } from '$lib/chatService.svelte'
import { queryLimits } from '$lib/limits.svelte'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data, fetch }) => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  const [comparisons, limits] = await Promise.all([
    queryComparisons(fetch, true),
    // Read from the browser only: the server's request carries neither the
    // person's session cookie nor their IP, so it would read someone else's.
    browser ? queryLimits(fetch) : null
  ])
  return { ...data, comparisons, limits }
}
