import { resetConsent } from '$lib/consent'
import { act, fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TOSModal from './TOSModal.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: null })
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
      title: 'Avant de **commencer**',
      introduction: 'Texte **configuré** avec [aide](https://example.test).',
      checkbox_label: '**Je confirme** ma participation.',
      button_label: '**Valider** et envoyer'
    },
    sign_in: { checkbox_label: 'Je confirme.' }
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
    return Promise.reject(new Error(`Unexpected request: ${path}`))
  })
}

describe('TOSModal', () => {
  beforeEach(() => {
    resetConsent()
    servesTerms()
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: (dialog: HTMLDialogElement) => ({
        modal: {
          disclose: () => dialog.setAttribute('open', ''),
          conceal: () => dialog.removeAttribute('open')
        }
      })
    })
  })

  it('waits for a message, then resumes it once the terms are accepted', async () => {
    const { component, container } = render(TOSModal)
    const dialog = container.querySelector<HTMLDialogElement>('#fr-modal-welcome')!
    const action = vi.fn()

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2))
    expect(dialog.hasAttribute('open')).toBe(false)
    expect(dialog.querySelector('h2 strong')?.textContent).toBe('commencer')
    expect(container.textContent).toContain('Texte configuré avec aide.')
    expect(dialog.querySelector('label strong')?.textContent).toBe('Je confirme')
    expect(container.textContent).toContain('Conditions générales d’utilisation')
    expect(container.textContent).toContain('Politique de confidentialité')

    await act(() => component.runAfterAcceptance(action))
    expect(dialog.hasAttribute('open')).toBe(true)
    expect(action).not.toHaveBeenCalled()

    await fireEvent.click(container.querySelector<HTMLInputElement>('#tos-modal')!)
    await fireEvent.click(container.querySelector<HTMLButtonElement>('.fr-modal__footer button')!)

    await waitFor(() => expect(action).toHaveBeenCalledOnce())
    expect(dialog.hasAttribute('open')).toBe(false)
    expect(mocks.request).toHaveBeenCalledWith(
      '/auth/consent/anonymous',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('sends straight away when the session already accepted the version in force', async () => {
    servesTerms(true)
    const { component, container } = render(TOSModal)
    const dialog = container.querySelector<HTMLDialogElement>('#fr-modal-welcome')!
    const action = vi.fn()

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2))
    await act(() => component.runAfterAcceptance(action))

    expect(action).toHaveBeenCalledOnce()
    expect(dialog.hasAttribute('open')).toBe(false)
  })

  it('cancels the pending send without losing the ability to retry', async () => {
    const { component, container } = render(TOSModal)
    const dialog = container.querySelector<HTMLDialogElement>('#fr-modal-welcome')!
    const action = vi.fn()

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2))
    await act(() => component.runAfterAcceptance(action))
    await fireEvent.click(container.querySelector<HTMLButtonElement>('.fr-modal__header button')!)

    expect(action).not.toHaveBeenCalled()
    expect(dialog.hasAttribute('open')).toBe(false)
    expect(
      mocks.request.mock.calls.filter(([, options]) => options?.method === 'POST')
    ).toHaveLength(0)

    await act(() => component.runAfterAcceptance(action))
    expect(dialog.hasAttribute('open')).toBe(true)
  })

  it('offers a working retry when the terms cannot be loaded', async () => {
    mocks.request.mockRejectedValue(new Error('offline'))
    const { component, container } = render(TOSModal)
    const dialog = container.querySelector<HTMLDialogElement>('#fr-modal-welcome')!
    const action = vi.fn()

    await waitFor(() => expect(container.textContent).toContain('n’ont pas pu être chargées'))
    expect(container.querySelector('#tos-modal')).toBeNull()

    await act(() => component.runAfterAcceptance(action))
    expect(dialog.hasAttribute('open')).toBe(true)
    expect(action).not.toHaveBeenCalled()

    servesTerms()
    await fireEvent.click(container.querySelector<HTMLButtonElement>('.fr-modal__footer button')!)

    await waitFor(() => expect(container.querySelector('#tos-modal')).not.toBeNull())
    await fireEvent.click(container.querySelector<HTMLInputElement>('#tos-modal')!)
    await fireEvent.click(container.querySelector<HTMLButtonElement>('.fr-modal__footer button')!)

    await waitFor(() => expect(action).toHaveBeenCalledOnce())
  })
})
