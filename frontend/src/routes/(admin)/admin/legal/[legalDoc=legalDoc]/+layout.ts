import { api } from '$lib/fastapi-client'
import type { AdminLegalDocument } from '$lib/generated/admin'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ params, fetch }) => {
  const endpoint = `/admin/legal/documents/${params.legalDoc}`
  return {
    documents: {
      history: await api.request<AdminLegalDocument[]>(endpoint, { fetch }),
      current: await api
        .request<AdminLegalDocument>(`${endpoint}/current`, {
          fetch
        })
        .catch(() => null)
    }
  }
}
