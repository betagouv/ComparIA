import { api } from '$lib/fastapi-client'
import type { AppSettingsPublic } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch }) => {
  return {
    settings: await api.request<AppSettingsPublic>('/admin/settings', { fetch })
  }
}
