import { queryComparisons } from '$lib/chatService.svelte'
import type { LayoutLoad } from './$types'

export const ssr = false // auth error on server side

export const load: LayoutLoad = async () => {
  // Unauthorized errors are handled globally, see hooks.client.ts

  return {
    comparisons: await queryComparisons()
  }
}
