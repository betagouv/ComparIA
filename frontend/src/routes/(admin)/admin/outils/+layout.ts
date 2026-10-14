import { api } from '$lib/fastapi-client'
import type { ToolAdmin } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ fetch, depends }) => {
  depends('admin:tools')
  const data = await api.request<{ tools: ToolAdmin[] }>('/admin/tools/data', { fetch })
  const schemas = await api.request<{ tools: JSONSchema }>('/admin/tools/schemas', { fetch })

  return { ...data, schemas }
}
