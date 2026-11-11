import type { AdminLegalDocument } from '$lib/generated/admin'
import type { LegalDocumentKeys } from '$lib/generated/constants'
import { adminLegalDocument } from '$lib/testing/mock-data'
import { render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { PageData } from './$types'
import Page from './+page.svelte'

vi.mock('$lib/authContext.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/authContext.svelte')>()),
  getAuthContext: () => ({ config: { default_locale: 'fr', enabled_locales: ['fr', 'en'] } })
}))

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
  it('hides the warning once real terms are published', async () => {
    const { getByRole, queryByRole } = renderPage('terms')
    await waitFor(() => expect(getByRole('heading', { name: 'Version 1.0' })).toBeTruthy())
    expect(queryByRole('heading', { name: 'Conditions d’exemple en vigueur' })).toBeNull()
  })

  it('shows nothing is yet published', async () => {
    const { getByRole } = renderPage('privacy_policy', null)
    await waitFor(() =>
      expect(getByRole('heading', { name: 'Aucune version publiée' })).toBeTruthy()
    )
  })
})
