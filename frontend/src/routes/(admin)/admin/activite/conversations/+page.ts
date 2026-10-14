import { api } from '$lib/fastapi-client'
import type { ActivityConversationsPage } from '$lib/generated/admin'
import { CONVERSATION_FILTERS, SHARED_FILTERS, errorMessage, pick } from '../filters'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch, url }) => {
  const searchParams = pick(url.searchParams, [
    ...SHARED_FILTERS,
    ...CONVERSATION_FILTERS,
    'cursor'
  ])
  // The backend refuses a search under three characters rather than scanning
  // every prompt for one letter.
  if ((searchParams.get('search') ?? '').length < 3) searchParams.delete('search')
  try {
    const conversations = await api.request<ActivityConversationsPage>(
      '/admin/activity/conversations',
      { fetch, searchParams }
    )
    return { conversations, error: null }
  } catch (error) {
    return { conversations: null, error: errorMessage(error) }
  }
}
