import { api } from '$lib/fastapi-client'
import type { LegalStatuses } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:legal')
  return {
    status: await api.request<LegalStatuses>('/admin/legal/status', { fetch })
  }
}
