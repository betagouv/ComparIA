import type { AdminLegalDocument } from '$lib/generated/admin'
import type { LegalDocumentKeys } from '$lib/generated/constants'
import { adminLegalDocument } from '$lib/testing/mock-data'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { PageData } from './$types'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: vi.fn() }))

function publishedBody(endpoint: string) {
  const call = mocks.request.mock.calls.find(
    ([path, options]) => path === endpoint && options?.method === 'POST'
  )
  return JSON.parse(call?.[1]?.body as string)
}

function renderPage(
  key: LegalDocumentKeys,
  current: AdminLegalDocument | null = adminLegalDocument(),
  history: AdminLegalDocument[] = current ? [current] : []
) {
  return render(Page, {
    data: { documents: { history, current } } as PageData,
    params: { legalDoc: key }
  })
}

describe('Legal document administration', () => {
  it('publishes a first privacy policy only after explicit confirmation', async () => {
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/documents/privacy_policy' && options?.method === 'POST') {
        return Promise.resolve(adminLegalDocument({ kind: 'privacy_policy' }))
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })

    const { getByRole } = renderPage('privacy_policy', null)

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
        '/admin/legal/documents/privacy_policy',
        expect.objectContaining({ method: 'POST' })
      )
    )
    expect(publishedBody('/admin/legal/documents/privacy_policy')).toMatchObject({
      version: '2026.1',
      locale: 'fr',
      content: '# Confidentialité\n\nTexte **important**.',
      confirm_publication: true
    })
  })
})
