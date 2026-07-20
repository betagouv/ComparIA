import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SignInForm from './SignInForm.svelte'
import SignInModal from './SignInModal.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  storeConsent: vi.fn(),
  authContext: {
    user: null,
    config: { access_policy: 'anonymous_first' as 'anonymous_first' | 'sign_in_required' }
  }
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => mocks.authContext
}))

vi.mock('$lib/chatService.svelte', () => ({
  getComparisonsContext: () => [],
  updateComparisonsContext: vi.fn()
}))

vi.mock('$lib/captcha.svelte', () => ({
  consumeAltchaToken: () => Promise.resolve('captcha-token')
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/consent', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/consent')>()),
  storeConsent: mocks.storeConsent
}))

vi.mock('$lib/i18n/runtime', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/i18n/runtime')>()),
  getLocale: () => 'fr'
}))

describe('SignInForm consent', () => {
  beforeEach(() => {
    mocks.authContext.config.access_policy = 'anonymous_first'
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path.startsWith('/settings/legal/terms')) {
        return Promise.resolve({
          version: '2026-07-20',
          content_hash: 'a'.repeat(64),
          locale: 'fr',
          presentation: {
            arena: {
              title: 'Avant de commencer',
              introduction: 'Introduction',
              checkbox_label: 'Je confirme.',
              links: [],
              button_label: null
            },
            sign_in: {
              checkbox_label: 'J’accepte avant de recevoir le code.',
              links: [{ label: 'Conditions', href: '/arene/modalites' }]
            }
          }
        })
      }
      if (path === '/auth/consent/anonymous' && !options?.method)
        return Promise.resolve({ terms: null })
      if (path === '/auth/consent/anonymous' && options?.method === 'POST')
        return Promise.resolve(undefined)
      if (path === '/auth/email/request') return Promise.resolve(undefined)
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
  })

  it('does not request a code until required consent is checked', async () => {
    const { container } = render(SignInForm)
    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())

    const email = container.querySelector<HTMLInputElement>('#login-email')!
    await fireEvent.input(email, { target: { value: 'personne@example.test' } })
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    await fireEvent.click(submit)

    expect(mocks.request.mock.calls.some(([path]) => path === '/auth/email/request')).toBe(false)
    expect(container.textContent).toContain('Vous devez accepter')

    await fireEvent.click(container.querySelector<HTMLInputElement>('#login-consent')!)
    await fireEvent.click(submit)

    await waitFor(() =>
      expect(mocks.request.mock.calls.some(([path]) => path === '/auth/email/request')).toBe(true)
    )
    const consentPostIndex = mocks.request.mock.calls.findIndex(
      ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
    )
    const emailRequestIndex = mocks.request.mock.calls.findIndex(
      ([path]) => path === '/auth/email/request'
    )
    expect(consentPostIndex).toBeGreaterThan(-1)
    expect(consentPostIndex).toBeLessThan(emailRequestIndex)
  })

  it('does not ask again when the anonymous session has accepted the current version', async () => {
    const fallback = mocks.request.getMockImplementation()!
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/auth/consent/anonymous' && !options?.method) {
        return Promise.resolve({
          terms: {
            version: '2026-07-20',
            content_hash: 'a'.repeat(64),
            locale: 'fr',
            accepted_at: '2026-07-20T10:00:00.000Z'
          }
        })
      }
      return fallback(path, options)
    })

    const { container } = render(SignInForm)
    const email = container.querySelector<HTMLInputElement>('#login-email')!
    await fireEvent.input(email, { target: { value: 'personne@example.test' } })
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    await waitFor(() => expect(submit.disabled).toBe(false))

    expect(container.querySelector('#login-consent')).toBeNull()
    await fireEvent.click(submit)
    await waitFor(() =>
      expect(mocks.request.mock.calls.some(([path]) => path === '/auth/email/request')).toBe(true)
    )
    expect(
      mocks.request.mock.calls.filter(
        ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
      )
    ).toHaveLength(0)
  })

  it('does not offer to merge anonymous conversations when sign-in is required', async () => {
    mocks.authContext.config.access_policy = 'sign_in_required'

    const { container } = render(SignInForm)

    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())
    expect(container.querySelector('#login-merge')).toBeNull()
    expect(container.textContent).not.toContain('Fusionner les conversations existantes')
  })

  it('keeps the accepted consent visible while entering the confirmation code', async () => {
    const { container } = render(SignInForm)
    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())

    await fireEvent.input(container.querySelector<HTMLInputElement>('#login-email')!, {
      target: { value: 'personne@example.test' }
    })
    await fireEvent.click(container.querySelector<HTMLInputElement>('#login-consent')!)
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)

    await waitFor(() => expect(container.querySelector('#login-code')).not.toBeNull())
    const consent = container.querySelector<HTMLInputElement>('#login-consent')
    expect(consent).not.toBeNull()
    expect(consent?.checked).toBe(true)
    expect(consent?.disabled).toBe(true)
  })

  it('does not display platform-specific data-use copy in the sign-in modal', async () => {
    const { container } = render(SignInModal)
    await waitFor(() => expect(container.querySelector('#login-email')).not.toBeNull())

    expect(container.textContent).not.toContain('Comment mes données sont-elles utilisées')
    expect(container.textContent).not.toContain('Les jeux de données compar:IA')
  })
})
