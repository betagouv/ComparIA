import { api } from '$lib/fastapi-client'
import type { TranslatableLegalPresentation } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:participation')
  return {
    presentations: await api.request<TranslatableLegalPresentation>('/admin/legal/presentation', {
      fetch
    })
  }
}
