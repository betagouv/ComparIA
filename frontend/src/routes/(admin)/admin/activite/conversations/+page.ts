import { api } from '$lib/fastapi-client'
import type { ActivityConversationsPage, ActivityStoppedMessagesPage } from '$lib/generated/admin'
import { CONVERSATION_FILTERS, SHARED_FILTERS, STOPPED, errorMessage, pick } from '../filters'
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
    if (searchParams.get('flag') === STOPPED) {
      // Their own list: only the period and the search apply to them.
      const stopped = await api.request<ActivityStoppedMessagesPage>(
        '/admin/activity/stopped-messages',
        { fetch, searchParams: pick(searchParams, ['period', 'start', 'end', 'search', 'cursor']) }
      )
      return { conversations: null, stopped, error: null }
    }
    const conversations = await api.request<ActivityConversationsPage>(
      '/admin/activity/conversations',
      { fetch, searchParams }
    )
    return { conversations, stopped: null, error: null }
  } catch (error) {
    return { conversations: null, stopped: null, error: errorMessage(error) }
  }
}
