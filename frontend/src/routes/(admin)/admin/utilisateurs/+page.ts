import { api } from '$lib/fastapi-client'
import type { UserPublic } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export type UsersPage = {
  items: UserPublic[]
  total: number
  page: number
  page_size: number
}

export const load: PageLoad = async ({ depends, url, fetch }) => {
  const search = url.searchParams.get('search') ?? ''
  const searchParams = new URLSearchParams({
    page: url.searchParams.get('page') ?? '1',
    page_size: url.searchParams.get('page_size') ?? '25'
  })
  if (search) searchParams.set('search', search)

  const users = await api.request<UsersPage>('/admin/users', { fetch, searchParams })

  depends('admin:users')

  return { search, users }
}
