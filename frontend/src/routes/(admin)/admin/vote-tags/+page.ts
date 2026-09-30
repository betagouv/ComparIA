import { api } from '$lib/fastapi-client'
import type { AdminVoteTagsResponse } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch, data }) => {
  depends('admin:vote-tags')

  return {
    ...data,
    voteTags: await api.request<AdminVoteTagsResponse>('/admin/vote-tags', { fetch })
  }
}
