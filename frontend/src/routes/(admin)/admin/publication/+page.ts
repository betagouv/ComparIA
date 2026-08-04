import { api } from '$lib/fastapi-client'
import type {
  AdminPublishDestinationsResponse,
  AdminPublishStatus
} from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:publishing')

  const [destinations, status] = await Promise.all([
    api.request<AdminPublishDestinationsResponse>('/admin/publishing/destinations', {
      fetch
    }),
    api.request<AdminPublishStatus>('/admin/publishing/status', { fetch })
  ])

  return { destinations, status }
}
