import { browser } from '$app/environment'
import { api } from '$lib/fastapi-client'
import type { PageLoad } from './$types'

export type ToolUsage = { id: string; calls: number; failures: number }
export type ToolHealth = {
  id: string
  ok: boolean
  error:
    | 'no_credential'
    | 'no_url'
    | 'invalid_credential'
    | 'no_credit'
    | 'unreachable'
    | 'timeout'
    | 'unknown_builtin'
    | null
  checked_at: string
}

export const load: PageLoad = async ({ fetch, depends }) => {
  depends('admin:tools')
  return {
    usage: await api.request<ToolUsage[]>('/admin/tools/usage', { fetch }),
    // Not awaited: checking every server can take seconds, and the list
    // should not wait for it. Left to the browser, since a check the server
    // started would be dropped unfinished and run a second time.
    health: browser
      ? api.request<ToolHealth[]>('/admin/tools/health', { fetch })
      : new Promise<ToolHealth[]>(() => {})
  }
}
