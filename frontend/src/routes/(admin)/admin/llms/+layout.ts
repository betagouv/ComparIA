import { api } from '$lib/fastapi-client'
import type { LLMData, LLMEndpoint, LLMLab, LLMLicense } from '$lib/generated/admin'
import type { LayoutLoad } from './$types'

export const ssr = false // auth error on server side

export const load: LayoutLoad = async () => {
  const data = await api.request<{
    endpoints: LLMEndpoint[]
    licenses: LLMLicense[]
    labs: LLMLab[]
    llms: LLMData[]
  }>('/admin/llms/data')

  return data
}
