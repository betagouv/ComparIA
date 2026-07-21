import { act, fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TOSModal from './TOSModal.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), storeConsent: vi.fn() }))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: null })
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

describe('TOSModal', () => {
  beforeEach(() => {
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path.startsWith('/settings/legal/terms')) {
        return Promise.resolve({
          version: '2026-07-20',
          content_hash: 'a'.repeat(64),
          locale: 'fr',
          presentation: {
            arena: {
              title: 'Avant de **commencer**',
              introduction: 'Texte **configuré** pour le test avec [aide](https://example.test).',
              checkbox_label:
                '**Je confirme** ma participation avec [le détail](https://example.test/conditions).',
              button_label: '**Valider** et envoyer'
            },
            sign_in: { checkbox_label: 'Je confirme.' }
          }
        })
      }
      if (path === '/auth/consent/anonymous' && options?.method === 'POST') {
        return Promise.resolve(undefined)
      }
      if (path === '/auth/consent/anonymous') return Promise.resolve({ terms: null })
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })

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

  it('waits for message submission, then resumes it after acceptance', async () => {
    const { component, container } = render(TOSModal)
    const dialog = container.querySelector<HTMLDialogElement>('#fr-modal-welcome')!
    const action = vi.fn()

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2))
    expect(dialog.hasAttribute('open')).toBe(false)
    expect(container.textContent).toContain('Texte configuré pour le test avec aide.')
    expect(dialog.querySelector('h2 strong')?.textContent).toBe('commencer')
    expect(dialog.querySelector('.fr-modal__content .fr-text--sm strong')?.textContent).toBe(
      'configuré'
    )
    expect(dialog.querySelector('a[href="https://example.test"]')).not.toBeNull()
    expect(dialog.querySelector('label strong')?.textContent).toBe('Je confirme')
    expect(container.textContent).toContain('Conditions générales d’utilisation')
    expect(container.textContent).toContain('Politique de confidentialité')
    expect(container.textContent).not.toContain('Lire les conditions')

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
      mocks.request.mock.calls.filter(
        ([path, options]) => path === '/auth/consent/anonymous' && options?.method === 'POST'
      )
    ).toHaveLength(0)

    await act(() => component.runAfterAcceptance(action))
    expect(dialog.hasAttribute('open')).toBe(true)
  })
})
