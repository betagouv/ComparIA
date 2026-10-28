import { api } from '$lib/fastapi-client'
import type {
  AdminPublishDestinationsResponse,
  AdminPublishStatus,
  DatasetCheckPublic
} from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { PromptCheckModel } from '../prompt-checks/types'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:publishing')

  const [destinations, status, datasetCheck, datasetCheckSchema, models] = await Promise.all([
    api.request<AdminPublishDestinationsResponse>('/admin/publishing/destinations', {
      fetch
    }),
    api.request<AdminPublishStatus>('/admin/publishing/status', { fetch }),
    api.request<DatasetCheckPublic>('/admin/dataset-check', { fetch }),
    api.request<JSONSchema>('/admin/dataset-check/schema', { fetch }),
    // The list only helps typing: the field takes any id.
    api
      .request<PromptCheckModel[]>('/admin/prompt-check/models', { fetch })
      .catch(() => [] as PromptCheckModel[])
  ])

  return { destinations, status, datasetCheck, datasetCheckSchema, models }
}
