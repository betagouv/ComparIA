import { api } from '$lib/fastapi-client'
import type { Tool } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { LayoutLoad } from './$types'

export const ssr = false // auth error on server side

export const load: LayoutLoad = async () => {
  const data = await api.request<{ tools: Tool[] }>('/admin/tools/data')
  const schemas = await api.request<{ tools: JSONSchema }>('/admin/tools/schemas')

  return { ...data, schemas }
}
