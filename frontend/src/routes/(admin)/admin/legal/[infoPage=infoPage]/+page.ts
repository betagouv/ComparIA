import { api } from '$lib/fastapi-client'
import type { InformationalLegalPage } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ params, depends, fetch }) => {
  depends('admin:informational-page')
  return {
    page: await api.request<Required<InformationalLegalPage>>(
      `/admin/legal/informational-page/${params.infoPage}`,
      { fetch }
    )
  }
}
