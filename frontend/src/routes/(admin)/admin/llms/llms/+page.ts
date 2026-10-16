import { api } from '$lib/fastapi-client'
import type { LLMDailyUsage } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch }) => {
  // The list still shows when today's spend cannot be read.
  const usage = await api.request<LLMDailyUsage[]>('/admin/llms/usage', { fetch }).catch(() => null)
  return { usage }
}
