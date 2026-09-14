import { resetConsent } from '$lib/consent'
import { expectAccessible } from '$lib/testing/a11y'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SignInForm from './SignInForm.svelte'
import SignInModal from './SignInModal.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  conceal: vi.fn(),
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
    mocks.conceal.mockClear()
    mocks.authContext.config.access_policy = 'anonymous_first'
    servesTerms()
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { conceal: mocks.conceal } })
    })
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

  it('clears the code and error before changing the email address', async () => {
    servesTerms(true)
    const { container, getByRole } = render(SignInForm)
    const emailInput = container.querySelector<HTMLInputElement>('#login-email')!
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    await waitFor(() => expect(submit.disabled).toBe(false))

    await fireEvent.input(emailInput, { target: { value: 'personne@example.test' } })
    await fireEvent.click(submit)

    const codeInput = await waitFor(() => {
      const input = container.querySelector<HTMLInputElement>('#login-code')
      expect(input).not.toBeNull()
      return input!
    })
    await fireEvent.input(codeInput, { target: { value: '123456' } })
    await expectAccessible(container)
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)
    await waitFor(() => expect(container.textContent).toContain('Code invalide ou expiré.'))

    const changeEmail = getByRole('button', { name: 'Modifier l’adresse email' })
    expect(changeEmail).toHaveAttribute('type', 'button')
    await fireEvent.click(changeEmail)

    expect(container.querySelector('#login-code')).toBeNull()
    expect(container.textContent).not.toContain('Code invalide ou expiré.')
    expect(emailInput.disabled).toBe(false)
    expect(document.activeElement).toBe(emailInput)

    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)
    await waitFor(() => {
      expect(container.querySelector<HTMLInputElement>('#login-code')?.value).toBe('')
    })
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

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2))
    expect(mocks.request).toHaveBeenNthCalledWith(
      1,
      '/settings/legal/terms',
      expect.objectContaining({ searchParams: { locale: 'fr' } })
    )
    expect(mocks.request).toHaveBeenNthCalledWith(2, '/auth/consent/anonymous')
  })

  it('does not repeat platform data-use copy next to the consent checkbox', async () => {
    const { container } = render(SignInModal)
    await waitFor(() => expect(container.querySelector('#login-email')).not.toBeNull())

    expect(container.textContent).not.toContain('Comment mes données sont-elles utilisées')
    expect(container.textContent).not.toContain('Les jeux de données compar:IA')
  })

  it('closes the modal before navigating to a legal document', async () => {
    const { container } = render(SignInModal)
    await waitFor(() => expect(container.querySelector('a[href="/privacy"]')).not.toBeNull())
    const privacyLink = container.querySelector<HTMLAnchorElement>('a[href="/privacy"]')!

    await fireEvent.click(privacyLink)

    expect(mocks.conceal).toHaveBeenCalledOnce()
  })

  it('hides the merge option when authentication is required', async () => {
    mocks.authContext.config.access_policy = 'sign_in_required'
    const { container } = render(SignInForm)

    await waitFor(() => expect(container.querySelector('#login-consent')).not.toBeNull())
    expect(container.querySelector('#login-merge')).toBeNull()
  })
})

describe('SignInForm authenticator step', () => {
  const me = { user: { email: 'admin@example.test', role: 'admin', totp_enabled: true } }

  function servesSignIn(totp: (code: string) => Promise<unknown>) {
    servesTerms(true)
    const base = mocks.request.getMockImplementation()!
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/auth/email/verify')
        return Promise.resolve({ email: 'admin@example.test', totp_required: true })
      if (path === '/auth/totp/verify') return totp(JSON.parse(options!.body as string).code)
      if (path === '/auth/me') return Promise.resolve(me)
      return base(path, options)
    })
  }

  async function reachTheAuthenticatorStep(container: HTMLElement) {
    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    await waitFor(() => expect(submit.disabled).toBe(false))
    await fireEvent.input(container.querySelector<HTMLInputElement>('#login-email')!, {
      target: { value: 'admin@example.test' }
    })
    await fireEvent.click(submit)
    const codeInput = await waitFor(() => container.querySelector<HTMLInputElement>('#login-code')!)
    await fireEvent.input(codeInput, { target: { value: '123456' } })
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)
    return waitFor(() => {
      const input = container.querySelector<HTMLInputElement>('#login-totp')
      expect(input).not.toBeNull()
      return input!
    })
  }

  beforeEach(() => {
    resetConsent()
    mocks.authContext.config.access_policy = 'anonymous_first'
    mocks.authContext.user = null
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { conceal: mocks.conceal } })
    })
  })

  it('asks for the authenticator code before fetching the account', async () => {
    servesSignIn(() => Promise.resolve({ email: 'admin@example.test' }))
    const onSuccess = vi.fn()
    const { container } = render(SignInForm, { props: { onSuccess } })

    const totpInput = await reachTheAuthenticatorStep(container)
    expect(paths()).not.toContain('/auth/me')
    expect(onSuccess).not.toHaveBeenCalled()
    expect(container.querySelector('#login-code')).toBeNull()
    expect(container.querySelector<HTMLInputElement>('#login-email')!.disabled).toBe(true)
    await waitFor(() => expect(document.activeElement).toBe(totpInput))
    await expectAccessible(container)

    const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!
    expect(submit.disabled).toBe(true)
    await fireEvent.input(totpInput, { target: { value: '65 43 21' } })
    expect(totpInput.value).toBe('654321')
    expect(submit.disabled).toBe(false)
    await fireEvent.click(submit)

    await waitFor(() => expect(onSuccess).toHaveBeenCalledOnce())
    const verify = mocks.request.mock.calls.find(([path]) => path === '/auth/totp/verify')!
    expect(JSON.parse(verify[1]!.body as string)).toEqual({ code: '654321' })
    expect(paths().indexOf('/auth/me')).toBeGreaterThan(paths().indexOf('/auth/totp/verify'))
    expect(mocks.authContext.user).toEqual(me.user)
  })

  it('reports a wrong authenticator code and lets the visitor retry', async () => {
    servesSignIn(() => Promise.reject(Object.assign(new Error('Invalid'), { status: 400 })))
    const { container } = render(SignInForm)

    const totpInput = await reachTheAuthenticatorStep(container)
    await fireEvent.input(totpInput, { target: { value: '000000' } })
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)

    await waitFor(() => expect(container.textContent).toContain('Code incorrect.'))
    expect(container.querySelector('#login-totp')).not.toBeNull()
    expect(paths()).not.toContain('/auth/me')
  })

  it('starts over when the half-finished sign-in has expired', async () => {
    servesSignIn(() => Promise.reject(Object.assign(new Error('Gone'), { status: 410 })))
    const { container } = render(SignInForm)

    const totpInput = await reachTheAuthenticatorStep(container)
    await fireEvent.input(totpInput, { target: { value: '000000' } })
    await fireEvent.click(container.querySelector<HTMLButtonElement>('button[type="submit"]')!)

    await waitFor(() => expect(container.textContent).toContain('Connexion expirée'))
    expect(container.querySelector('#login-totp')).toBeNull()
    expect(container.querySelector('#login-code')).toBeNull()
    expect(container.querySelector<HTMLInputElement>('#login-email')!.disabled).toBe(false)
  })
})
