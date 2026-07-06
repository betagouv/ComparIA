import { api } from '$lib/fastapi-client'
import type { APILLMData } from '$lib/generated/backend'
import type { PageLoad } from './$types'

export const ssr = false // auth error on server side

export const load: PageLoad = async () => {
  // FIXME types
  const llms = await api.request<APILLMData[]>('/admin/llms/list')

  return {
    llms
  }
}
