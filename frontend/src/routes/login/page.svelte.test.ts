import { resetConsent } from '$lib/consent'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  replaceState: vi.fn(),
  pageState: { url: new URL('http://localhost/login') },
  authContext: {
    user: null,
    config: {
      access_policy: 'sign_in_required',
      methods: ['oidc'] as string[],
      oidc_enabled: true,
      oidc_button_label: 'Se connecter avec ProConnect',
      oidc_has_button_logo: false,
      platform_name: 'Compar:IA',
      has_custom_logo: false
    }
  }
}))

vi.mock('$app/navigation', () => ({ goto: vi.fn(), replaceState: mocks.replaceState }))
vi.mock('$app/paths', () => ({ resolve: (path: string) => path, match: vi.fn() }))
vi.mock('$app/state', () => ({ page: mocks.pageState }))
vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => mocks.authContext }))
vi.mock('$lib/authContext.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/authContext.svelte')>()),
  getPlatformName: () => 'Compar:IA',
  tryGetAuthContext: () => mocks.authContext
}))
vi.mock('$lib/captcha.svelte', () => ({ consumeAltchaToken: () => Promise.resolve('token') }))
vi.mock('$lib/chatService.svelte', () => ({
  getComparisonsContext: () => [],
  updateComparisonsContext: vi.fn()
}))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request, getUrl: (path: string) => path }
}))
vi.mock('$lib/i18n/runtime', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/i18n/runtime')>()),
  getLocale: () => 'fr'
}))

const terms = {
  version: '2026-07-20',
  content_hash: 'a'.repeat(64),
  locale: 'fr',
  presentation: {
    arena: {
      title: 'Avant de commencer',
      introduction: 'Introduction',
      checkbox_label: 'Je confirme.',
      button_label: null
    },
    sign_in: { checkbox_label: 'J’accepte avant de me connecter.' }
  }
}

function visit(search = '') {
  mocks.pageState.url = new URL(`http://localhost/login${search}`)
}

describe('login page', () => {
  beforeEach(() => {
    resetConsent()
    mocks.request.mockReset()
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path.startsWith('/settings/legal/terms')) return Promise.resolve(terms)
      if (path === '/auth/consent/anonymous') return Promise.resolve({ terms: null })
      if (path === '/auth/totp/verify' && options?.method === 'POST')
        return Promise.reject(Object.assign(new Error('Gone'), { status: 410 }))
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
    mocks.authContext.config.methods = ['oidc']
    mocks.authContext.config.oidc_enabled = true
    visit()
  })

  const errorMessages: Record<string, string> = {
    account_unavailable: 'désactivé ou supprimé',
    domain_not_allowed: 'domaine autorisé',
    email_not_verified: 'n’a pas confirmé votre adresse',
    invalid_nonce: 'jeton invalide',
    invalid_state: 'a expiré',
    missing_code: 'est incomplète',
    no_email: 'n’a pas renvoyé d’adresse',
    oidc_unavailable: 'n’est pas activée',
    provider_error: 'a refusé la demande',
    rate_limited: 'Trop de tentatives',
    terms_required: 'Acceptez les conditions'
  }

  for (const [code, text] of Object.entries(errorMessages)) {
    it(`explains the ${code} error code`, async () => {
      visit(`?error=${code}`)
      const { getByRole } = render(Page)
      expect(getByRole('alert').textContent).toContain(text)
    })
  }

  it('shows no message for an unknown error code', () => {
    visit('?error=whatever')
    const { queryByRole } = render(Page)
    expect(queryByRole('alert')).toBeNull()
  })

  it('leads back to the SSO button when the authenticator challenge expires on an SSO-only instance', async () => {
    visit('?step=totp&redirect=%2Fadmin')
    const { container, getByRole } = render(Page)

    await fireEvent.input(container.querySelector<HTMLInputElement>('#login-totp')!, {
      target: { value: '000000' }
    })
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)

    await waitFor(() => expect(getByRole('alert').textContent).toContain('fournisseur d’identité'))
    expect(container.querySelector('#login-totp')).toBeNull()
    expect(container.querySelector('#login-email')).toBeNull()
    expect(container.textContent).toContain('Se connecter avec ProConnect')
  })
})
