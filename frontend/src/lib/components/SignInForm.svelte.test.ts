import { resetConsent } from '$lib/consent'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SignInForm from './SignInForm.svelte'
import SignInModal from './SignInModal.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  authContext: { user: null, config: { access_policy: 'anonymous_first' } }
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
    sign_in: { checkbox_label: 'J’accepte avant de recevoir le code.' }
  }
}

function servesTerms(accepted = false) {
  mocks.request.mockImplementation((path: string, options?: RequestInit) => {
    if (path.startsWith('/settings/legal/terms')) return Promise.resolve(terms)
    if (path === '/auth/consent/anonymous' && options?.method === 'POST')
      return Promise.resolve(undefined)
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
    if (path === '/auth/email/request') return Promise.resolve(undefined)
    return Promise.reject(new Error(`Unexpected request: ${path}`))
  })
}

const paths = () => mocks.request.mock.calls.map(([path]) => path)

describe('SignInForm consent', () => {
  beforeEach(() => {
    resetConsent()
    mocks.authContext.config.access_policy = 'anonymous_first'
    servesTerms()
  })

  it('does not request a code until the terms are accepted', async () => {
    const { container } = render(SignInForm)
    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())

    await fireEvent.input(container.querySelector<HTMLInputElement>('#login-email')!, {
      target: { value: 'personne@example.test' }
    })
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    expect(submit.disabled).toBe(true)
    await fireEvent.click(submit)

    expect(paths()).not.toContain('/auth/email/request')

    await fireEvent.click(container.querySelector<HTMLInputElement>('#login-consent')!)
    expect(submit.disabled).toBe(false)
    await fireEvent.click(submit)

    await waitFor(() => expect(paths()).toContain('/auth/email/request'))
    const consentPost = mocks.request.mock.calls.findIndex(
      ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
    )
    expect(consentPost).toBeGreaterThan(-1)
    expect(consentPost).toBeLessThan(paths().indexOf('/auth/email/request'))
  })

  it('does not ask again when the session already accepted the version in force', async () => {
    servesTerms(true)
    const { container } = render(SignInForm)
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    await waitFor(() => expect(submit.disabled).toBe(false))

    await fireEvent.input(container.querySelector<HTMLInputElement>('#login-email')!, {
      target: { value: 'personne@example.test' }
    })
    await fireEvent.click(submit)

    await waitFor(() => expect(paths()).toContain('/auth/email/request'))
    expect(
      mocks.request.mock.calls.filter(
        ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
      )
    ).toHaveLength(0)
    expect(container.querySelector<HTMLInputElement>('#login-consent')?.disabled).toBe(true)
  })

  it('offers a working retry when the terms cannot be loaded', async () => {
    mocks.request.mockRejectedValue(new Error('offline'))
    const { container } = render(SignInForm)

    await waitFor(() => expect(container.textContent).toContain('n’ont pas pu être chargées'))
    expect(container.querySelector('#login-consent')).toBeNull()
    expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(true)

    servesTerms()
    const retry = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Réessayer'
    )!
    await fireEvent.click(retry)

    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())
    expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(true)

    await fireEvent.click(container.querySelector<HTMLInputElement>('#login-consent')!)
    expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(
      false
    )
  })

  it('shares the consent request with the rest of the page', async () => {
    render(SignInForm)
    render(SignInForm)

    // Each form fetches its own signup questions, so count the consent paths
    // rather than every call: two forms, one shared consent request.
    const consentPaths = () =>
      paths().filter((path: string) => !path.startsWith('/survey/questions'))

    await waitFor(() => expect(consentPaths().length).toBe(2))
    expect(consentPaths()).toEqual(['/settings/legal/terms?locale=fr', '/auth/consent/anonymous'])
  })

  it('does not repeat platform data-use copy next to the consent checkbox', async () => {
    const { container } = render(SignInModal)
    await waitFor(() => expect(container.querySelector('#login-email')).not.toBeNull())

    expect(container.textContent).not.toContain('Comment mes données sont-elles utilisées')
    expect(container.textContent).not.toContain('Les jeux de données compar:IA')
  })

  it('hides the merge option when authentication is required', async () => {
    mocks.authContext.config.access_policy = 'sign_in_required'
    const { container } = render(SignInForm)

    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())
    expect(container.querySelector('#login-merge')).toBeNull()
  })
})
