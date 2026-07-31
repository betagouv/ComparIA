import { api } from '$lib/fastapi-client'
import type { PromptCheckStatus } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  const check = await api.request<PromptCheckStatus>('/admin/prompt-check', { fetch })

  depends('admin:prompt-check')

  return { check }
}
