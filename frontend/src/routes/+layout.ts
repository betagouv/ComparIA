import type { AuthUser } from '$lib/auth.svelte'
import { api } from '$lib/fastapi-client'
import type {
  AuthConfig,
  InformationalLegalPageLinks,
  LLMList,
  PublicCookieBanner,
  PublicSurveyResponse
} from '$lib/generated/backend'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import { emptySurvey } from '$lib/survey.svelte'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ data: serverData, fetch, depends }) => {
  depends('survey:signup')
  const locale = getLocale()

  // The switch and measurement the server rendered with, not a fresh read: the
  // browser must ask exactly when the server held Matomo back.
  const { cookieBannerEnabled, measurement } = serverData
  // Without its text the banner stays hidden, which only puts off the question.
  const cookieBannerRequest =
    cookieBannerEnabled && measurement
      ? api
          .request<PublicCookieBanner>('/settings/legal/cookies', {
            fetch,
            searchParams: { locale }
          })
          .catch((error: Error) => {
            console.error(`Unable to load the cookie banner: ${error.message}`)
            return null
          })
      : Promise.resolve(null)

  const [votes, data, authConfig, auth, informationalPagesLinks, survey] = await Promise.all([
    api.request<VotesData>('/counter', { fetch }),
    api.request<LLMList>('/models/', { fetch }),
    api.request<AuthConfig>('/auth/config', { fetch }),
    api.request<{ user: AuthUser | null }>('/auth/me', { fetch }),
    api.request<InformationalLegalPageLinks>('/settings/legal/informational-pages-links', {
      fetch
    }),
    // A survey outage must never take a page down: both degrade exactly
    // like no questions being configured at all.
    api
      .request<PublicSurveyResponse>('/survey', {
        fetch,
        searchParams: { locale }
      })
      .catch((error: Error) => {
        console.error(`Unable to load survey signup questions: ${error.message}`)
        return emptySurvey
      })
  ])
  const cookieBanner = await cookieBannerRequest

  return {
    data,
    votes,
    auth: { user: auth.user, config: authConfig },
    informationalPagesLinks,
    survey,
    cookieBannerEnabled,
    measurement,
    cookieBanner
  }
}
