import { api } from '$lib/fastapi-client'
import type { UserPublic } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, url, fetch }) => {
  const params = new URLSearchParams({
    page: url.searchParams.get('page') ?? '1',
    page_size: url.searchParams.get('page_size') ?? '50'
  })
  const data = await api.request<{ items: UserPublic[]; total: number }>(`/admin/users?${params}`, {
    fetch
  })

  depends('admin:users')

  return {
    users: data
  }
}
