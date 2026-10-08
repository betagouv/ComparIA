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

export const load: PageLoad = async () => {
  return {
    usage: await api.request<ToolUsage[]>('/admin/tools/usage'),
    // Not awaited: checking every server can take seconds, and the list
    // should not wait for it.
    health: api.request<ToolHealth[]>('/admin/tools/health')
  }
}
