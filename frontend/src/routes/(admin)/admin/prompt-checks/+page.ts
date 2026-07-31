import { api } from '$lib/fastapi-client'
import type { PromptCheckStatus } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  const checks = await api.request<PromptCheckStatus[]>('/admin/prompt-checks', { fetch })

  depends('admin:prompt-checks')

  return { checks }
}
