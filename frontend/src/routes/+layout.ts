import type { AuthConfig, AuthUser } from '$lib/auth.svelte'
import { api } from '$lib/fastapi-client'
import type {
  LLMList,
  MySurveyAnswersResponse,
  PublicSurveyQuestionsResponse
} from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import { emptySurveyQuestions } from '$lib/survey'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ fetch, depends }) => {
  const locale = getLocale()
  const votes = await api.request<VotesData>('/counter', { fetch })
  const data = await api.request<LLMList>('/models/', { fetch })
  const authConfig = await api.request<AuthConfig>('/auth/config', { fetch })
  const auth = await api.request<{ user: AuthUser | null }>('/auth/me', { fetch })

  depends('survey:signup')
  const surveySignupQuestions = await api
    .request<PublicSurveyQuestionsResponse>(`/survey/questions?locale=${locale}&trigger=signup`)
    .catch((error: Error) => {
      // A survey outage must never block sign-in: this degrades exactly like
      // no questions being configured at all.
      console.error(`Unable to load survey signup questions: ${error.message}`)
      return emptySurveyQuestions
    })
  const surveySignupAnswers = await api.request<MySurveyAnswersResponse>('/survey/me', {
    fetch,
    searchParams: { locale }
  })

  return {
    data,
    votes,
    auth: { user: auth.user, config: authConfig },
    survey: {
      signupQuestions: surveySignupQuestions.questions,
      signupAnswers: surveySignupAnswers.answers
    }
  }
}
