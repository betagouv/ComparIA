import type { AppSettingsPublic } from '$lib/generated/admin'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageProps } from './$types'
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

vi.mock('$app/navigation', () => ({ beforeNavigate: vi.fn() }))
vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))
vi.mock('$lib/authContext.svelte', () => ({
  getAuthContext: () => auth,
  tryGetAuthContext: () => auth
}))
vi.mock('$lib/global.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/global.svelte')>()),
  getVotesContext: () => votes
}))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn(), getPublicUrl: (path: string) => path },
  ValidationError: class extends Error {}
}))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: vi.fn() }))

const settings = (votesObjective: number): AppSettingsPublic => ({
  auth_access_policy: 'anonymous_first',
  auth_domain_allowlist: [],
  votes_objective: votesObjective,
  ranking_min_votes: 0,
  ranking_max_rank_spread: 30,
  survey_reask_after_days: 7,
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

function renderPage() {
  const props = { data: { settings: settings(300_000) } } as unknown as PageProps
  return render(Page, props)
}

async function lastRequestBody() {
  const { api } = await import('$lib/fastapi-client')
  await waitFor(() => expect(api.request).toHaveBeenCalledTimes(1))
  return JSON.parse(vi.mocked(api.request).mock.calls[0][1]!.body as string)
}

describe('admin customization page', () => {
  beforeEach(async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValueOnce(settings(450_000))
    votes.objective = 300_000
  })

  it('updates the live sidebar vote objective after saving', async () => {
    const { container } = renderPage()
    const input = container.querySelector<HTMLInputElement>('#votes_objective')!

    await fireEvent.input(input, { target: { value: '450000' } })
    await fireEvent.submit(input.closest('form')!)

    await waitFor(() => expect(votes.objective).toBe(450_000))
  })

  it('sends the leaderboard thresholds on save', async () => {
    const { container } = renderPage()
    const minVotes = container.querySelector<HTMLInputElement>('#ranking_min_votes')!
    const spread = container.querySelector<HTMLInputElement>('#ranking_max_rank_spread')!

    await fireEvent.input(minVotes, { target: { value: '50' } })
    await fireEvent.input(spread, { target: { value: '60' } })
    await fireEvent.submit(minVotes.closest('form')!)

    expect(await lastRequestBody()).toMatchObject({
      ranking_min_votes: 50,
      ranking_max_rank_spread: 60
    })
  })

  it('sends the home texts per locale on save', async () => {
    const { container } = renderPage()
    const title = container.querySelector<HTMLInputElement>('#home_title-input')!
    expect(title.value).toBe('Posez votre question')

    await fireEvent.click(container.querySelector('#home_prompt_placeholder-en')!)
    const placeholder = container.querySelector<HTMLInputElement>('#home_prompt_placeholder-input')!
    await fireEvent.input(placeholder, { target: { value: 'Ask your health question' } })
    await fireEvent.submit(title.closest('form')!)

    expect(await lastRequestBody()).toMatchObject({
      home_title: { fr: 'Posez votre question' },
      home_prompt_placeholder: { en: 'Ask your health question' }
    })
  })

  it('stops the home texts at the length the backend accepts', () => {
    const { container } = renderPage()
    const maxlength = (id: string) => container.querySelector(id)!.getAttribute('maxlength')

    expect(maxlength('#home_title-input')).toBe('200')
    expect(maxlength('#home_prompt_placeholder-input')).toBe('200')
    expect(maxlength('#home_banner-input')).toBe('1000')
  })

  it('refuses a primary colour that is too light to read on white', async () => {
    const { api } = await import('$lib/fastapi-client')
    const { container, findByText } = renderPage()
    const color = container.querySelector<HTMLInputElement>('#primary_color_light')!

    await fireEvent.input(color, { target: { value: '#FFFF00' } })
    await fireEvent.submit(color.closest('form')!)

    expect(color.getAttribute('aria-invalid')).toBe('true')
    expect(await findByText(/contraste/i, { selector: '.fr-message--error' })).toBeTruthy()
    expect(api.request).not.toHaveBeenCalled()
  })
})
