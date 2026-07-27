import { api } from '$lib/fastapi-client'
import type { PublicSuggestions } from '$lib/suggestions'
import type { LayoutServerLoad } from './$types'

const emptySuggestions: PublicSuggestions = { categories: [] }

export const load: LayoutServerLoad = async ({ cookies, fetch }) => {
  const locale = cookies.get('PARAGLIDE_LOCALE') ?? 'fr'

  try {
    return {
      suggestions: await api.request<PublicSuggestions>(
        `/suggestions?locale=${encodeURIComponent(locale)}`,
        { fetch }
      )
    }
  } catch (error) {
    // Suggestions are optional: the arena must remain usable if curated content
    // is temporarily unavailable.
    console.error(`Unable to load guided suggestions: ${(error as Error).message}`)
    return { suggestions: emptySuggestions }
  }
}
