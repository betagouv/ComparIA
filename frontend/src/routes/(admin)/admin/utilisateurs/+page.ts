import { api } from '$lib/fastapi-client'
import type { UserPublic } from '$lib/generated/admin'
import { redirect } from '@sveltejs/kit'
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

  // Deleting the only user on the last page leaves that page empty, and the
  // table hides its pagination when there are no rows, so go back to the last
  // page that still has some.
  if (users.total > 0 && users.items.length === 0 && users.page > 1) {
    const lastPage = Math.ceil(users.total / users.page_size)
    searchParams.set('page', String(lastPage))
    redirect(303, `${url.pathname}?${searchParams.toString()}`)
  }

  depends('admin:users')

  return { search, users }
}
