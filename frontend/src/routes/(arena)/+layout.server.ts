import { api } from '$lib/fastapi-client'
import { loadInformationalPages } from '$lib/informational-pages.server'
import type { PublicSuggestions } from '$lib/suggestions'
import { emptyVoteTags, type PublicVoteTags } from '$lib/voteTags'
import type { LayoutServerLoad } from './$types'

const emptySuggestions: PublicSuggestions = { categories: [] }

export const load: LayoutServerLoad = async ({ cookies, fetch }) => {
  const locale = cookies.get('PARAGLIDE_LOCALE') ?? 'fr'
  const options = { fetch, searchParams: { locale } }

  const [suggestions, voteTags, informationalPages] = await Promise.all([
    api.request<PublicSuggestions>('/suggestions', options).catch((error: Error) => {
      // Suggestions are optional: the arena must remain usable if curated content
      // is temporarily unavailable.
      console.error(`Unable to load guided suggestions: ${error.message}`)
      return emptySuggestions
    }),
    api.request<PublicVoteTags>('/vote-tags', options).catch((error: Error) => {
      // A voter can still pick a side and leave a comment without the tags,
      // so the arena stays usable and only loses the chips.
      console.error(`Unable to load vote tags: ${error.message}`)
      return emptyVoteTags
    }),
    loadInformationalPages(fetch)
  ])

  return { suggestions, voteTags: voteTags.tags, informationalPages }
}
