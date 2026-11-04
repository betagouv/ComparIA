import type { AppSettingsPublic } from '$lib/generated/admin'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const auth = {
  config: {
    platform_name: 'ComparIA',
    primary_color_light: '#000091',
    primary_color_dark: '#8585F6',
    secondary_color_light: '#A558A0',
    secondary_color_dark: '#D176CF',
    homepage_url: null,
    enabled_locales: ['fr', 'en'],
    default_locale: 'fr'
  }
}
const votes = { count: 148, objective: 300_000 }

vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))
vi.mock('$lib/authContext.svelte', () => ({
  getAuthContext: () => auth,
  tryGetAuthContext: () => auth
}))
vi.mock('$lib/global.svelte', () => ({
  getVotesContext: () => votes,
  getLocales: (codes: string[]) => codes.map((code) => ({ code, short: code, long: code }))
}))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn(), getPublicUrl: (path: string) => path }
}))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: vi.fn() }))

const settings = (votesObjective: number): AppSettingsPublic => ({
  auth_access_policy: 'anonymous_first',
  auth_domain_allowlist: [],
  votes_objective: votesObjective,
  ranking_min_votes: 0,
  ranking_max_rank_spread: 30,
  platform_name: 'ComparIA',
  primary_color_light: '#000091',
  primary_color_dark: '#8585F6',
  secondary_color_light: '#A558A0',
  secondary_color_dark: '#D176CF',
  homepage_url: null,
  home_title: { fr: 'Posez votre question' },
  home_prompt_placeholder: {},
  home_banner: {},
  analysis_endpoint_id: null,
  analysis_model: null,
  publish_frequency: 'off',
  publish_hour: 3,
  publish_timezone: 'UTC',
  has_custom_logo: false,
  enabled_locales: ['fr', 'en'],
  default_locale: 'fr',
  auth_methods: ['email_code'],
  oidc_issuer: null,
  oidc_client_id: null,
  oidc_has_client_secret: false,
  oidc_scopes: [],
  oidc_button_label: null,
  oidc_has_button_logo: false,
  oidc_button_logo_content_type: null,
  updated_at: '2026-09-13T13:59:34.551785',
  updated_by: null
})

describe('admin customization page', () => {
  beforeEach(async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request)
      .mockResolvedValueOnce(settings(300_000))
      .mockResolvedValueOnce(settings(450_000))
    votes.objective = 300_000
  })

  it('updates the live sidebar vote objective after saving', async () => {
    const { container } = render(Page)
    await waitFor(() => expect(container.querySelector('#settings-votes-objective')).not.toBeNull())
    const input = container.querySelector<HTMLInputElement>('#settings-votes-objective')!

    await fireEvent.input(input, { target: { value: '450000' } })
    await fireEvent.submit(input.closest('form')!)

    await waitFor(() => expect(votes.objective).toBe(450_000))
  })

  it('sends the leaderboard thresholds on save', async () => {
    const { api } = await import('$lib/fastapi-client')
    const { container } = render(Page)
    await waitFor(() =>
      expect(container.querySelector('#settings-ranking-min-votes')).not.toBeNull()
    )
    const minVotes = container.querySelector<HTMLInputElement>('#settings-ranking-min-votes')!
    const spread = container.querySelector<HTMLInputElement>('#settings-ranking-max-rank-spread')!

    await fireEvent.input(minVotes, { target: { value: '50' } })
    await fireEvent.input(spread, { target: { value: '60' } })
    await fireEvent.submit(minVotes.closest('form')!)

    await waitFor(() => expect(api.request).toHaveBeenCalledTimes(2))
    const body = JSON.parse(vi.mocked(api.request).mock.calls[1][1]!.body as string)
    expect(body).toMatchObject({ ranking_min_votes: 50, ranking_max_rank_spread: 60 })
  })

  it('sends the home texts per locale on save', async () => {
    const { api } = await import('$lib/fastapi-client')
    const { container } = render(Page)
    await waitFor(() =>
      expect(container.querySelector('#settings-home-title-input')).not.toBeNull()
    )
    const title = container.querySelector<HTMLInputElement>('#settings-home-title-input')!
    expect(title.value).toBe('Posez votre question')

    await fireEvent.click(container.querySelector('#settings-home-prompt-placeholder-en')!)
    const placeholder = container.querySelector<HTMLInputElement>(
      '#settings-home-prompt-placeholder-input'
    )!
    await fireEvent.input(placeholder, { target: { value: 'Ask your health question' } })
    await fireEvent.submit(title.closest('form')!)

    await waitFor(() => expect(api.request).toHaveBeenCalledTimes(2))
    const body = JSON.parse(vi.mocked(api.request).mock.calls[1][1]!.body as string)
    expect(body).toMatchObject({
      home_title: { fr: 'Posez votre question' },
      home_prompt_placeholder: { en: 'Ask your health question' }
    })
  })

  it('stops the home texts at the length the backend accepts', async () => {
    const { container } = render(Page)
    await waitFor(() =>
      expect(container.querySelector('#settings-home-title-input')).not.toBeNull()
    )
    expect(container.querySelector('#settings-home-title-input')!.getAttribute('maxlength')).toBe(
      '200'
    )
    expect(
      container.querySelector('#settings-home-prompt-placeholder-input')!.getAttribute('maxlength')
    ).toBe('200')
    expect(container.querySelector('#settings-home-banner-input')!.getAttribute('maxlength')).toBe(
      '1000'
    )
  })
})
