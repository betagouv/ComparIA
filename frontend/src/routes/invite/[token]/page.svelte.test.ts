import { resetConsent } from '$lib/consent'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InvitePage from './+page.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), goto: vi.fn() }))

vi.mock('$app/state', () => ({ page: { params: { token: 'invite-token' } } }))

vi.mock('$app/navigation', () => ({ goto: mocks.goto }))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: null, config: null })
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: vi.fn() }))

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
    sign_in: { checkbox_label: 'J’accepte avant de rejoindre.' }
  }
}

function servesTerms({ accepted = false, consentFails = false } = {}) {
  mocks.request.mockImplementation((path: string, options?: RequestInit) => {
    if (path === '/auth/invite/invite-token')
      return Promise.resolve({ valid: true, email: 'personne@example.test' })
    if (consentFails) return Promise.reject(new Error('offline'))
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
    if (path === '/auth/invite/accept') return Promise.resolve({ success: true })
    if (path === '/auth/me') return Promise.resolve({ user: { email: 'personne@example.test' } })
    return Promise.reject(new Error(`Unexpected request: ${path}`))
  })
}

const paths = () => mocks.request.mock.calls.map(([path]) => path)

const acceptButton = (container: HTMLElement) =>
  [...container.querySelectorAll<HTMLButtonElement>('button')].find(
    (button) => button.textContent?.trim() === 'Accepter et continuer'
  )!

describe('invite consent', () => {
  beforeEach(() => {
    resetConsent()
    servesTerms()
  })

  it('does not accept the invite until the terms are accepted', async () => {
    const { container } = render(InvitePage)
    await waitFor(() => expect(container.querySelector('#invite-consent')).not.toBeNull())

    expect(acceptButton(container).disabled).toBe(true)
    await fireEvent.click(acceptButton(container))

    expect(paths()).not.toContain('/auth/invite/accept')

    await fireEvent.click(container.querySelector<HTMLInputElement>('#invite-consent')!)
    expect(acceptButton(container).disabled).toBe(false)
    await fireEvent.click(acceptButton(container))

    await waitFor(() => expect(paths()).toContain('/auth/invite/accept'))
    const consentPost = mocks.request.mock.calls.findIndex(
      ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
    )
    expect(consentPost).toBeGreaterThan(-1)
    expect(consentPost).toBeLessThan(paths().indexOf('/auth/invite/accept'))
  })

  it('does not ask again when the visitor already accepted the version in force', async () => {
    servesTerms({ accepted: true })
    const { container } = render(InvitePage)
    await waitFor(() => expect(acceptButton(container).disabled).toBe(false))

    await fireEvent.click(acceptButton(container))

    await waitFor(() => expect(paths()).toContain('/auth/invite/accept'))
    expect(
      mocks.request.mock.calls.filter(
        ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
      )
    ).toHaveLength(0)
    expect(container.querySelector<HTMLInputElement>('#invite-consent')?.disabled).toBe(true)
  })

  it('offers a working retry when the terms cannot be loaded', async () => {
    servesTerms({ consentFails: true })
    const { container } = render(InvitePage)

    await waitFor(() => expect(container.textContent).toContain('n’ont pas pu être chargées'))
    expect(container.querySelector('#invite-consent')).toBeNull()
    expect(acceptButton(container).disabled).toBe(true)

    servesTerms()
    const retry = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Réessayer'
    )!
    await fireEvent.click(retry)

    await waitFor(() => expect(container.querySelector('#invite-consent')).not.toBeNull())
    expect(acceptButton(container).disabled).toBe(true)

    await fireEvent.click(container.querySelector<HTMLInputElement>('#invite-consent')!)
    expect(acceptButton(container).disabled).toBe(false)
  })

  it('shows the terms and privacy links next to the checkbox', async () => {
    const { container } = render(InvitePage)
    await waitFor(() => expect(container.querySelector('#invite-consent-links')).not.toBeNull())

    const links = [...container.querySelectorAll<HTMLAnchorElement>('#invite-consent-links a')]
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/arene/modalites',
      '/arene/donnees-personnelles'
    ])
  })
})
