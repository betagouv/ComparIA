import { api } from '$lib/fastapi-client'
import type {
  AdminPublishDestinationsResponse,
  AdminPublishStatus,
  AppSettingsPublic,
  LLMEndpoint
} from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:publishing')

  const [destinations, status, settings, llmData] = await Promise.all([
    api.request<AdminPublishDestinationsResponse>('/admin/publishing/destinations', {
      fetch
    }),
    api.request<AdminPublishStatus>('/admin/publishing/status', { fetch }),
    api.request<AppSettingsPublic>('/admin/settings', { fetch }),
    api.request<{ endpoints: LLMEndpoint[] }>('/admin/llms/data', { fetch })
  ])

  return { destinations, status, settings, endpoints: llmData.endpoints }
}
