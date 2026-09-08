import { api } from '$lib/fastapi-client'
import type { PersonalRanking } from '$lib/generated/backend'

export type RankingView = 'general' | 'personal'

export async function load({ fetch, url, parent }) {
  const { auth } = await parent()
  const view: RankingView = url.searchParams.get('view') === 'personal' ? 'personal' : 'general'

  // The layout's model data is the same for everyone, so it cannot carry a
  // ranking built from one account's votes. Fetched here, and only when that
  // view is open, so it is as fresh as the user's last vote.
  if (view !== 'personal' || !auth.user) return { view, personal: null, personalFailed: false }

  // A wobbling backend should cost the personal panel, not the whole route:
  // api.request throws on a non-OK response, which SvelteKit turns into an
  // error page for the general ranking too.
  try {
    return {
      view,
      personal: await api.request<PersonalRanking>('/ranking/personal', { fetch }),
      personalFailed: false
    }
  } catch {
    return { view, personal: null, personalFailed: true }
  }
}
