import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import { PRIVACY_POLICY_PATH, TERMS_PATH, ACCESSIBILITY_PATH, ECODESIGN_PATH } from '$lib/consent'
import { expectAccessible } from '$lib/testing/a11y'

const request = vi.fn()
const mocks = vi.hoisted(() => ({
  auth: { user: { email: 'personne@example.org', role: 'user', totp_enabled: false } },
  url: new URL('http://localhost/settings'),
  goto: vi.fn(),
  toast: vi.fn(),
  disclose: vi.fn(),
  conceal: vi.fn()
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => mocks.auth,
  logout: vi.fn()
}))
vi.mock('$app/navigation', () => ({ goto: mocks.goto }))
// Only the query string is driven by the tests; the rest of `page` stays real.
vi.mock('$app/state', async (importOriginal) => {
  const original = await importOriginal<typeof import('$app/state')>()
  return {
    ...original,
    page: new Proxy(original.page, {
      get: (target, prop) => (prop === 'url' ? mocks.url : Reflect.get(target, prop))
    })
  }
})
vi.mock('$app/paths', () => ({ resolve: (path: string) => path }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))

vi.mock('$lib/chatService.svelte', () => ({ getComparisonsContext: () => [] }))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: (...args: unknown[]) => request(...args) }
}))

describe('Settings page', () => {
  it('splits the account actions from the legal information', async () => {
    const { container, getByRole, getByLabelText } = render(Page)

    expect(getByRole('heading', { level: 1, name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('tab', { name: 'Compte' }).getAttribute('aria-selected')).toBe('true')
    expect(getByLabelText('Adresse électronique').hasAttribute('disabled')).toBe(true)
    expect(getByRole('button', { name: 'Se déconnecter' })).toBeTruthy()
    expect(getByRole('button', { name: 'Exporter mes données' })).toBeTruthy()

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(getByRole('heading', { name: 'Liens utiles' })).toBeTruthy()
    expect(
      getByRole('link', { name: 'Conditions générales d’utilisation' }).getAttribute('href')
    ).toBe(TERMS_PATH)
    expect(getByRole('link', { name: 'Politique de confidentialité' }).getAttribute('href')).toBe(
      PRIVACY_POLICY_PATH
    )
    expect(getByRole('link', { name: /Accessibilité/ }).getAttribute('href')).toBe(
      ACCESSIBILITY_PATH
    )
    expect(getByRole('link', { name: 'Écoconception' }).getAttribute('href')).toBe(ECODESIGN_PATH)
    // Tabs keeps every panel in the DOM and hides the inactive ones through
    // the DSFR styles, so the selected class is what separates them here.
    expect(container.querySelector('#tab-about-panel')).toHaveClass('fr-tabs__panel--selected')
    expect(container.querySelector('#tab-account-panel')).not.toHaveClass(
      'fr-tabs__panel--selected'
    )
  })

  it('asks the backend for the export rather than building it in the page', async () => {
    request.mockResolvedValue({ schema_version: 1, conversations: [], consents: [] })
    const { getByRole } = render(Page)

    await fireEvent.click(getByRole('button', { name: 'Exporter mes données' }))

    await waitFor(() => expect(request).toHaveBeenCalledWith('/auth/me/export'))
  })

  it('only enables the erasure once the account address is retyped', async () => {
    const { container } = render(Page)

    const modal = container.querySelector('#account-erasure-modal')!
    const confirm = () =>
      [...modal.querySelectorAll('button')].find(
        (button) => button.textContent?.trim() === 'Supprimer mon compte'
      )!
    expect(confirm().disabled).toBe(true)
    expect(modal.textContent).toContain('personne@example.org')

    const field = modal.querySelector('#account-erasure-email')!
    await fireEvent.input(field, { target: { value: ' Personne@example.org ' } })

    await waitFor(() => expect(confirm().disabled).toBe(false))
  })
})

describe('Settings page two-factor section', () => {
  const setup = {
    secret: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
    otpauth_uri: 'otpauth://totp/x',
    qr_svg: 'data:image/svg+xml;charset=utf-8,%3Csvg%3E%3C/svg%3E'
  }

  beforeEach(() => {
    request.mockReset()
    mocks.goto.mockClear()
    mocks.toast.mockClear()
    mocks.disclose.mockClear()
    mocks.conceal.mockClear()
    mocks.auth.user = { email: 'admin@example.org', role: 'admin', totp_enabled: false }
    mocks.url = new URL('http://localhost/settings')
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { disclose: mocks.disclose, conceal: mocks.conceal } })
    })
  })

  it('is not shown to a plain user', () => {
    mocks.auth.user = { email: 'personne@example.org', role: 'user', totp_enabled: false }
    const { queryByRole } = render(Page)
    expect(queryByRole('heading', { name: 'Double authentification' })).toBeNull()
  })

  it('walks a new admin through the QR code and the first code', async () => {
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup' ? Promise.resolve(setup) : Promise.resolve(undefined)
    )
    const { container, getByRole } = render(Page)

    expect(getByRole('heading', { name: 'Double authentification' })).toBeTruthy()
    expect(container.textContent).toContain('Non configurée')
    await fireEvent.click(getByRole('button', { name: 'Configurer une application' }))

    await waitFor(() => expect(mocks.disclose).toHaveBeenCalledOnce())
    const modal = container.querySelector('#totp-setup-modal')!
    const img = await waitFor(() => modal.querySelector<HTMLImageElement>('img')!)
    expect(img.getAttribute('src')).toBe(setup.qr_svg)
    expect(modal.textContent).toContain('ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567')
    expect(request).toHaveBeenCalledWith(
      '/auth/totp/setup',
      expect.objectContaining({ body: '{}' })
    )
    await expectAccessible(container)

    const confirm = () =>
      [...modal.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Activer')!
    expect(confirm().disabled).toBe(true)
    await fireEvent.input(modal.querySelector('#totp-confirm-code')!, {
      target: { value: '123456' }
    })
    await waitFor(() => expect(confirm().disabled).toBe(false))
    await fireEvent.click(confirm())

    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        '/auth/totp/confirm',
        expect.objectContaining({ body: JSON.stringify({ code: '123456' }) })
      )
    )
    await waitFor(() => expect(mocks.conceal).toHaveBeenCalledOnce())
    // The mocked context is a plain object, so the badge flip itself is not
    // observable here; the flag the page sets on it is.
    expect(mocks.auth.user.totp_enabled).toBe(true)
    expect(mocks.toast).toHaveBeenCalledOnce()
    expect(mocks.goto).not.toHaveBeenCalled()
  })

  it('shows the loading state again when reopened after a cancel', async () => {
    let release = () => {}
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup'
        ? new Promise((resolve) => {
            release = () => resolve(setup)
          })
        : Promise.resolve(undefined)
    )
    const { container, getByRole } = render(Page)
    const modal = container.querySelector('#totp-setup-modal')!
    const open = () => fireEvent.click(getByRole('button', { name: 'Configurer une application' }))

    await open()
    release()
    await waitFor(() => expect(modal.querySelector('img')).not.toBeNull())
    // DSFR announces the cancel button with this event; the secret leaves the DOM.
    await fireEvent(modal, new Event('dsfr.conceal'))
    expect(modal.querySelector('img')).toBeNull()

    await open()
    await waitFor(() => expect(request).toHaveBeenCalledTimes(2))
    expect(modal.querySelector('.fr-alert')).toBeNull()
    expect(modal.textContent).not.toContain('La configuration n’a pas pu démarrer')
    expect(modal.textContent).toContain('Préparation…')

    release()
    await waitFor(() => expect(modal.querySelector('img')).not.toBeNull())
  })

  it('sends the admin back to the admin area when they were pushed here', async () => {
    mocks.url = new URL('http://localhost/settings?totp=required')
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup' ? Promise.resolve(setup) : Promise.resolve(undefined)
    )
    const { container, getByRole } = render(Page)

    expect(container.textContent).toContain('Configuration requise')
    await fireEvent.click(getByRole('button', { name: 'Configurer une application' }))
    const modal = container.querySelector('#totp-setup-modal')!
    await waitFor(() => expect(modal.querySelector('#totp-confirm-code')).not.toBeNull())
    await fireEvent.input(modal.querySelector('#totp-confirm-code')!, {
      target: { value: '123456' }
    })
    await fireEvent.click(
      [...modal.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Activer')!
    )

    await waitFor(() => expect(mocks.goto).toHaveBeenCalledWith('/admin'))
  })

  it('shows a wrong first code without closing', async () => {
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup'
        ? Promise.resolve(setup)
        : Promise.reject(Object.assign(new Error('Invalid'), { status: 400 }))
    )
    const { container, getByRole } = render(Page)

    await fireEvent.click(getByRole('button', { name: 'Configurer une application' }))
    const modal = container.querySelector('#totp-setup-modal')!
    await waitFor(() => expect(modal.querySelector('#totp-confirm-code')).not.toBeNull())
    await fireEvent.input(modal.querySelector('#totp-confirm-code')!, {
      target: { value: '000000' }
    })
    await fireEvent.click(
      [...modal.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Activer')!
    )

    await waitFor(() => expect(modal.textContent).toContain('Code incorrect.'))
    expect(mocks.conceal).not.toHaveBeenCalled()
    expect(mocks.auth.user.totp_enabled).toBe(false)
  })

  it('tells the admin to sign in again when the session ended mid-setup', async () => {
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup'
        ? Promise.resolve(setup)
        : Promise.reject(Object.assign(new Error('auth_required'), { status: 401 }))
    )
    const { container, getByRole } = render(Page)

    await fireEvent.click(getByRole('button', { name: 'Configurer une application' }))
    const modal = container.querySelector('#totp-setup-modal')!
    await waitFor(() => expect(modal.querySelector('#totp-confirm-code')).not.toBeNull())
    await fireEvent.input(modal.querySelector('#totp-confirm-code')!, {
      target: { value: '123456' }
    })
    await fireEvent.click(
      [...modal.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Activer')!
    )

    await waitFor(() => expect(modal.textContent).toContain('Session expirée, reconnectez-vous.'))
    expect(modal.textContent).not.toContain('Code incorrect.')
  })

  it('asks to start again when the backend wants a code the page did not know about', async () => {
    request.mockRejectedValue(
      Object.assign(new Error('Error 400 [POST](/auth/totp/setup): totp_code_required'), {
        status: 400
      })
    )
    const { container, getByRole } = render(Page)

    await fireEvent.click(getByRole('button', { name: 'Configurer une application' }))
    const modal = container.querySelector('#totp-setup-modal')!

    await waitFor(() => expect(modal.textContent).toContain('Recommencez depuis le début.'))
    expect(modal.textContent).not.toContain('Code incorrect.')
  })

  it('asks an enrolled admin for a code from the current device first', async () => {
    mocks.auth.user = { email: 'admin@example.org', role: 'admin', totp_enabled: true }
    request.mockImplementation((path: string) =>
      path === '/auth/totp/setup' ? Promise.resolve(setup) : Promise.resolve(undefined)
    )
    const { container, getByRole } = render(Page)

    expect(container.textContent).toContain('Activée')
    await fireEvent.click(getByRole('button', { name: 'Changer d’appareil' }))
    const modal = container.querySelector('#totp-setup-modal')!
    const current = await waitFor(() => modal.querySelector('#totp-current-code')!)
    expect(request).not.toHaveBeenCalled()

    await fireEvent.input(current, { target: { value: '654321' } })
    await fireEvent.click(
      [...modal.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Continuer')!
    )

    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        '/auth/totp/setup',
        expect.objectContaining({ body: JSON.stringify({ code: '654321' }) })
      )
    )
    await waitFor(() => expect(modal.querySelector('img')).not.toBeNull())
    expect(modal.textContent).toContain('Vos autres sessions seront déconnectées.')
  })
})
