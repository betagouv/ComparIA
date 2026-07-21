import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TermsDocumentAdmin from './TermsDocumentAdmin.svelte'

const activeDocument = {
  id: '11111111-1111-4111-8111-111111111111',
  kind: 'terms',
  version: '1.0',
  locale: 'fr',
  content: '# Conditions actives',
  content_hash: 'a'.repeat(64),
  published_at: '2026-07-20T10:00:00.000Z',
  effective_at: '2026-07-20T10:00:00.000Z',
  retired_at: null,
  presentation: {
    arena: {
      title: 'Avant de commencer',
      introduction: 'Introduction',
      checkbox_label: 'J’accepte.',
      links: [{ label: 'Conditions', href: '/arene/modalites' }],
      button_label: 'Continuer'
    },
    sign_in: {
      checkbox_label: 'J’accepte avant la connexion.',
      links: [{ label: 'Conditions', href: '/arene/modalites' }]
    }
  }
}

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))

describe('Terms document administration', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/terms' && options?.method === 'POST') {
        return Promise.resolve({ ...activeDocument, version: '2.0' })
      }
      if (path === '/admin/legal/terms') return Promise.resolve([activeDocument])
      if (path.startsWith('/admin/legal/terms/current')) return Promise.resolve(activeDocument)
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
  })

  it('edits the document without exposing journey copy fields', async () => {
    const { container, getByRole, queryByRole, queryByText } = render(TermsDocumentAdmin)
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    await fireEvent.click(getByRole('button', { name: 'Préparer une nouvelle version' }))

    expect(getByRole('textbox', { name: /Contenu des conditions/ })).toBeTruthy()
    expect(queryByRole('textbox', { name: /Titre de la fenêtre/ })).toBeNull()
    expect(queryByText(/parcours de participation actuel/)).toBeNull()
    expect(queryByText(/saisissez directement du Markdown/)).toBeNull()
    expect(container.querySelector('.fr-hint-text')).toBeNull()
  })

  it('keeps the publication step compact and aligned', async () => {
    const { container, getByRole, queryByRole, getByText } = render(TermsDocumentAdmin)
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    await fireEvent.click(getByRole('button', { name: 'Préparer une nouvelle version' }))
    await fireEvent.click(getByRole('button', { name: 'Continuer vers « Vérifier et publier »' }))

    expect(queryByRole('heading', { name: 'Publication définitive' })).toBeNull()
    expect(getByText('Langue du document publié.')).toBeTruthy()
    expect(
      container.querySelector('#terms-document-effective-at')?.closest('.fr-input-group')
    ).toHaveClass('fr-mt-4v')
  })

  it('publishes the new document while preserving the current journey', async () => {
    const { getByRole } = render(TermsDocumentAdmin)
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    await fireEvent.click(getByRole('button', { name: 'Préparer une nouvelle version' }))
    await fireEvent.input(getByRole('textbox', { name: /Contenu des conditions/ }), {
      target: { value: '# Nouvelles conditions' }
    })
    await fireEvent.click(getByRole('button', { name: 'Continuer vers « Vérifier et publier »' }))
    await fireEvent.input(getByRole('textbox', { name: /Référence de la nouvelle version/ }), {
      target: { value: '2.0' }
    })
    await fireEvent.click(getByRole('checkbox', { name: /J’ai relu les conditions/ }))
    await fireEvent.click(getByRole('button', { name: 'Publier ces conditions' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/terms',
        expect.objectContaining({ method: 'POST' })
      )
    )
    const body = JSON.parse(
      mocks.request.mock.calls.find(
        ([path, options]) => path === '/admin/legal/terms' && options?.method === 'POST'
      )?.[1]?.body as string
    )
    expect(body.content).toBe('# Nouvelles conditions')
    expect(body.presentation.arena.title).toBe('Avant de commencer')
    expect(body.presentation.sign_in.checkbox_label).toBe('J’accepte avant la connexion.')
  })
})
