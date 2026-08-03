import { api } from '$lib/fastapi-client'
import type { PublicSuggestions } from '$lib/suggestions'
import { emptyVoteTags, type PublicVoteTags } from '$lib/voteTags'
import type { LayoutServerLoad } from './$types'

const emptySuggestions: PublicSuggestions = { categories: [] }

export const load: LayoutServerLoad = async ({ cookies, fetch }) => {
  const locale = cookies.get('PARAGLIDE_LOCALE') ?? 'fr'

  const [suggestions, voteTags] = await Promise.all([
    api
      .request<PublicSuggestions>(`/suggestions?locale=${encodeURIComponent(locale)}`, { fetch })
      .catch((error: Error) => {
        // Suggestions are optional: the arena must remain usable if curated content
        // is temporarily unavailable.
        console.error(`Unable to load guided suggestions: ${error.message}`)
        return emptySuggestions
      }),
    api
      .request<PublicVoteTags>(`/vote-tags?locale=${encodeURIComponent(locale)}`, { fetch })
      .catch((error: Error) => {
        // A voter can still pick a side and leave a comment without the tags,
        // so the arena stays usable and only loses the chips.
        console.error(`Unable to load vote tags: ${error.message}`)
        return emptyVoteTags
      })
  ])

  return { suggestions, voteTags: voteTags.tags }
}
