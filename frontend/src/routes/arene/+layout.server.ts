import { api } from '$lib/fastapi-client'
import { emptySurveyQuestions, type PublicSurveyQuestionsResponse } from '$lib/survey'
import type { PublicSuggestions } from '$lib/suggestions'
import { emptyVoteTags, type PublicVoteTags } from '$lib/voteTags'
import type { LayoutServerLoad } from './$types'

const emptySuggestions: PublicSuggestions = { categories: [] }

export const load: LayoutServerLoad = async ({ cookies, fetch }) => {
  const locale = cookies.get('PARAGLIDE_LOCALE') ?? 'fr'

  const [suggestions, voteTags, surveyQuestions] = await Promise.all([
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
      }),
    api
      .request<PublicSurveyQuestionsResponse>(
        `/survey/questions?trigger=after_vote&locale=${encodeURIComponent(locale)}`,
        { fetch }
      )
      .catch((error: Error) => {
        // The post-vote popup is a nice-to-have: the reveal page must stay
        // usable if the survey service is temporarily unavailable.
        console.error(`Unable to load survey questions: ${error.message}`)
        return emptySurveyQuestions
      })
  ])

  return { suggestions, voteTags: voteTags.tags, surveyQuestions: surveyQuestions.questions }
}
