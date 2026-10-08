import { resetConsent } from '$lib/consent'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SSOSignIn from './SSOSignIn.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  authContext: { user: null, config: { access_policy: 'sign_in_required' } }
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => mocks.authContext
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

function servesTerms(accepted: boolean) {
  mocks.request.mockImplementation((path: string) => {
    if (path.startsWith('/settings/legal/terms')) return Promise.resolve(terms)
    if (path === '/auth/consent/anonymous')
      return Promise.resolve({
        terms: accepted
          ? {
              version: terms.version,
              content_hash: terms.content_hash,
              locale: terms.locale,
              accepted_at: '2026-07-20T10:00:00.000Z'
            }
          : null
      })
    return Promise.reject(new Error(`Unexpected request: ${path}`))
  })
}

async function renderButton(accepted: boolean) {
  servesTerms(accepted)
  const { container } = render(SSOSignIn, {
    props: { oidcLabel: 'Se connecter avec ProConnect', oidcLogoUrl: null }
  })
  await waitFor(() => expect(container.querySelector('#sso-consent')).not.toBeNull())
  return {
    container,
    button: container.querySelector<HTMLButtonElement>('button.fr-btn')!
  }
}

describe('SSOSignIn', () => {
  beforeEach(() => {
    resetConsent()
    mocks.request.mockReset()
  })

  it('is a primary call to action', async () => {
    const { button } = await renderButton(true)
    expect(button.textContent).toContain('Se connecter avec ProConnect')
    expect(button.classList.contains('fr-btn--primary')).toBe(true)
    expect(button.classList.contains('fr-btn--secondary')).toBe(false)
  })

  it('stays disabled until the terms are accepted', async () => {
    const { container, button } = await renderButton(false)
    expect(button.disabled).toBe(true)

    await fireEvent.click(container.querySelector<HTMLInputElement>('#sso-consent')!)
    expect(button.disabled).toBe(false)
  })

  it('is enabled at once when the session already accepted the terms', async () => {
    const { button } = await renderButton(true)
    await waitFor(() => expect(button.disabled).toBe(false))
  })
})
