import { api } from '$lib/fastapi-client'
import type { AdminVoteTagsResponse } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:vote-tags')

  return { voteTags: await api.request<AdminVoteTagsResponse>('/admin/vote-tags', { fetch }) }
}
