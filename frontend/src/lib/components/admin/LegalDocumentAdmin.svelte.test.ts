import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LegalDocumentAdmin from './LegalDocumentAdmin.svelte'

const activeTerms = {
  id: '11111111-1111-4111-8111-111111111111',
  kind: 'terms',
  version: '1.0',
  locale: 'fr',
  content: '# Conditions actives',
  content_hash: 'a'.repeat(64),
  published_at: '2026-07-20T10:00:00.000Z',
  effective_at: '2026-07-20T10:00:00.000Z',
  retired_at: null,
  seeded: false
}

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))

function publishedBody(endpoint: string) {
  const call = mocks.request.mock.calls.find(
    ([path, options]) => path === endpoint && options?.method === 'POST'
  )
  return JSON.parse(call?.[1]?.body as string)
}

describe('Legal document administration', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/terms' && options?.method === 'POST') {
        return Promise.resolve({ ...activeTerms, version: '2.0' })
      }
      if (path === '/admin/legal/terms') return Promise.resolve([activeTerms])
      if (path.startsWith('/admin/legal/terms/current')) return Promise.resolve(activeTerms)
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
  })

  it('edits the terms without exposing journey copy fields', async () => {
    const { getByRole, queryByRole } = render(LegalDocumentAdmin, { kind: 'terms' })
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    await fireEvent.click(getByRole('button', { name: 'Préparer une nouvelle version' }))

    expect(getByRole('textbox', { name: /Contenu des conditions/ })).toBeTruthy()
    expect(queryByRole('textbox', { name: /Titre de la fenêtre/ })).toBeNull()
  })

  it('warns while the seeded terms are still in force', async () => {
    mocks.request.mockImplementation((path: string) => {
      if (path === '/admin/legal/terms') return Promise.resolve([{ ...activeTerms, seeded: true }])
      if (path.startsWith('/admin/legal/terms/current')) {
        return Promise.resolve({ ...activeTerms, seeded: true })
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })

    const { getByRole } = render(LegalDocumentAdmin, { kind: 'terms' })
    await waitFor(() =>
      expect(getByRole('heading', { name: 'Conditions d’exemple en vigueur' })).toBeTruthy()
    )
  })

  it('hides the warning once real terms are published', async () => {
    const { getByRole, queryByRole } = render(LegalDocumentAdmin, { kind: 'terms' })
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    expect(queryByRole('heading', { name: 'Conditions d’exemple en vigueur' })).toBeNull()
  })

  it('publishes new terms without coupling them to the participation journey', async () => {
    const { getByRole } = render(LegalDocumentAdmin, { kind: 'terms' })
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    await fireEvent.click(getByRole('button', { name: 'Préparer une nouvelle version' }))
    await fireEvent.input(getByRole('textbox', { name: /Contenu des conditions/ }), {
      target: { value: '# Nouvelles conditions' }
    })
    await fireEvent.click(getByRole('button', { name: 'Continuer vers « Vérifier et publier »' }))
    await fireEvent.input(getByRole('textbox', { name: /Référence de la nouvelle version/ }), {
      target: { value: '2.0' }
    })
    await fireEvent.click(getByRole('checkbox', { name: /J’ai relu le document/ }))
    await fireEvent.click(getByRole('button', { name: 'Publier cette version' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/terms',
        expect.objectContaining({ method: 'POST' })
      )
    )
    const body = publishedBody('/admin/legal/terms')
    expect(body.content).toBe('# Nouvelles conditions')
    expect(body).not.toHaveProperty('presentation')
  })

  it('publishes a first privacy policy only after explicit confirmation', async () => {
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/privacy-policy' && options?.method === 'POST') {
        return Promise.resolve({ ...activeTerms, kind: 'privacy_policy' })
      }
      if (path === '/admin/legal/privacy-policy') return Promise.resolve([])
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })

    const { getByRole } = render(LegalDocumentAdmin, { kind: 'privacy_policy' })
    await waitFor(() =>
      expect(getByRole('heading', { name: 'Aucune version publiée' })).toBeTruthy()
    )

    await fireEvent.click(getByRole('button', { name: 'Publier une première version' }))
    await fireEvent.input(getByRole('textbox', { name: /Contenu de la politique/ }), {
      target: { value: '# Confidentialité\n\nTexte **important**.' }
    })
    await fireEvent.click(getByRole('button', { name: 'Continuer vers « Vérifier et publier »' }))
    expect(getByRole('combobox', { name: 'Langue' })).toBeTruthy()
    await fireEvent.input(getByRole('textbox', { name: /Référence de la nouvelle version/ }), {
      target: { value: '2026.1' }
    })
    await fireEvent.click(getByRole('checkbox', { name: /J’ai relu le document/ }))
    await fireEvent.click(getByRole('button', { name: 'Publier cette version' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/privacy-policy',
        expect.objectContaining({ method: 'POST' })
      )
    )
    expect(publishedBody('/admin/legal/privacy-policy')).toMatchObject({
      version: '2026.1',
      locale: 'fr',
      content: '# Confidentialité\n\nTexte **important**.',
      confirm_publication: true
    })
  })
})
