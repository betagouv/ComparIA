import { api } from '$lib/fastapi-client'
import type { AdminLimits } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:limits')
  return { limits: await api.request<AdminLimits>('/admin/limits', { fetch }) }
}
