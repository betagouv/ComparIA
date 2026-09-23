import type { AuthConfig, AuthUser } from '$lib/auth.svelte'
import { api } from '$lib/fastapi-client'
import type {
  LLMList,
  MySurveyAnswersResponse,
  PublicSurveyQuestionsResponse
} from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import { emptySurveyAnswers, emptySurveyQuestions } from '$lib/survey'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ fetch, depends }) => {
  depends('survey:signup')
  const locale = getLocale()

  const [votes, data, authConfig, auth, surveySignupQuestions, surveySignupAnswers] =
    await Promise.all([
      api.request<VotesData>('/counter', { fetch }),
      api.request<LLMList>('/models/', { fetch }),
      api.request<AuthConfig>('/auth/config', { fetch }),
      api.request<{ user: AuthUser | null }>('/auth/me', { fetch }),
      // A survey outage must never take a page down: both degrade exactly
      // like no questions being configured at all.
      api
        .request<PublicSurveyQuestionsResponse>('/survey/questions', {
          fetch,
          searchParams: { locale, trigger: 'signup' }
        })
        .catch((error: Error) => {
          console.error(`Unable to load survey signup questions: ${error.message}`)
          return emptySurveyQuestions
        }),
      api
        .request<MySurveyAnswersResponse>('/survey/me', { fetch, searchParams: { locale } })
        .catch((error: Error) => {
          console.error(`Unable to load survey answers: ${error.message}`)
          return emptySurveyAnswers
        })
    ])

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
