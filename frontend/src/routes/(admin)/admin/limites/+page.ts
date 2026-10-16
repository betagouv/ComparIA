import { api } from '$lib/fastapi-client'
import type { AdminLimits, LLMDailyUsage } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:limits')
  const [limits, usage] = await Promise.all([
    api.request<AdminLimits>('/admin/limits', { fetch }),
    // The page still sets the limits when today's spend cannot be read.
    api.request<LLMDailyUsage[]>('/admin/llms/usage', { fetch }).catch(() => null)
  ])
  return { limits, usage }
}
