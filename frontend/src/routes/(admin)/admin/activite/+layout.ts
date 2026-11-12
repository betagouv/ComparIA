import { api } from '$lib/fastapi-client'
import type { ActivityFilterOptions } from '$lib/generated/admin'
import { getLocale } from '$lib/i18n/runtime'
import { emptyVoteTags, type PublicVoteTags } from '$lib/voteTags'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ fetch }) => {
  // The filter bar and the tag names can do without, the counts below them
  // cannot wait on them: an empty list is better than no page.
  const [options, voteTags] = await Promise.all([
    api
      .request<ActivityFilterOptions>(`/admin/activity/filters?locale=${getLocale()}`, { fetch })
      .catch((): ActivityFilterOptions => ({ llms: [], modes: [], cohorts: [], categories: [] })),
    api.request<PublicVoteTags>('/vote-tags', { fetch }).catch(() => emptyVoteTags)
  ])

  return { options, voteTags: voteTags.tags }
}
