import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PrivacyPolicyAdmin from './PrivacyPolicyAdmin.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))

describe('Privacy policy administration', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/privacy-policy' && options?.method === 'POST') {
        return Promise.resolve({ id: 'privacy-policy-2' })
      }
      if (path === '/admin/legal/privacy-policy') return Promise.resolve([])
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
  })

  it('publishes a first Markdown policy only after explicit confirmation', async () => {
    const { container, getByRole, getByText, queryByRole, queryByText } = render(PrivacyPolicyAdmin)
    await waitFor(() =>
      expect(getByRole('heading', { name: 'Aucune politique publiée' })).toBeTruthy()
    )

    await fireEvent.click(getByRole('button', { name: 'Créer la politique de confidentialité' }))
    expect(
      container.querySelector('#privacy-policy-content-label')?.classList.contains('fr-mb-2v')
    ).toBe(true)
    expect(getByText('Aperçu').classList.contains('fr-label')).toBe(true)
    expect(getByText('Aperçu').classList.contains('fr-mb-2v')).toBe(true)
    expect(queryByText(/saisissez directement du Markdown/)).toBeNull()
    expect(container.querySelector('.fr-hint-text')).toBeNull()
    await fireEvent.input(getByRole('textbox', { name: /Contenu de la politique/ }), {
      target: { value: '# Confidentialité\n\nTexte **important**.' }
    })
    await fireEvent.click(getByRole('button', { name: 'Continuer vers « Vérifier et publier »' }))
    expect(queryByRole('heading', { name: 'Publication définitive' })).toBeNull()
    expect(queryByText('Langue du document publié.')).toBeNull()
    expect(getByRole('combobox', { name: 'Langue' })).toBeTruthy()
    expect(
      container
        .querySelector('#privacy-policy-effective-at')
        ?.closest('.fr-input-group')
        ?.classList.contains('fr-mt-4v')
    ).toBe(true)
    await fireEvent.input(getByRole('textbox', { name: /Référence de la nouvelle version/ }), {
      target: { value: '2026.1' }
    })
    await fireEvent.click(getByRole('checkbox', { name: /J’ai relu la politique/ }))
    await fireEvent.click(getByRole('button', { name: 'Publier cette politique' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/privacy-policy',
        expect.objectContaining({ method: 'POST' })
      )
    )
    const publishCall = mocks.request.mock.calls.find(
      ([path, options]) => path === '/admin/legal/privacy-policy' && options?.method === 'POST'
    )
    expect(JSON.parse(publishCall?.[1]?.body as string)).toMatchObject({
      version: '2026.1',
      locale: 'fr',
      content: '# Confidentialité\n\nTexte **important**.',
      confirm_publication: true
    })
  })
})
