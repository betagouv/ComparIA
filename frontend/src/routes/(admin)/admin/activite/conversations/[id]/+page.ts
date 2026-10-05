import { api, type ApiError } from '$lib/fastapi-client'
import type { ActivityConversation } from '$lib/generated/admin'
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch, params }) => {
  const conversation = await api
    .request<ActivityConversation>(`/admin/activity/conversations/${params.id}`, { fetch })
    .catch((err: ApiError) => error(err.status === 404 ? 404 : 500))
  return { conversation }
}
