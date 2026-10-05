import { api } from '$lib/fastapi-client'
import type { ActivityOverview } from '$lib/generated/admin'
import { SHARED_FILTERS, errorMessage, pick } from '../filters'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch, url }) => {
  const searchParams = pick(url.searchParams, SHARED_FILTERS)
  try {
    const overview = await api.request<ActivityOverview>('/admin/activity/overview', {
      fetch,
      searchParams
    })
    return { overview, error: null }
  } catch (error) {
    return { overview: null, error: errorMessage(error) }
  }
}
