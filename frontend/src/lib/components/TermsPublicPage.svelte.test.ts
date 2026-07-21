import { render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from '../../routes/arene/modalites/+page.svelte'

const mocks = vi.hoisted(() => ({ getActiveTerms: vi.fn() }))

vi.mock('$lib/consent', () => ({
  getActiveTerms: mocks.getActiveTerms
}))

describe('Public terms page', () => {
  it('shows the active terms without redundant navigation buttons', async () => {
    mocks.getActiveTerms.mockResolvedValue({
      version: '2026.1',
      hash: 'terms-hash',
      locale: 'fr',
      content: '# Conditions générales d’utilisation\n\nContenu des conditions.',
      publishedAt: '2026-07-20T12:00:00Z',
      effectiveAt: '2026-07-20T12:00:00Z',
      presentation: {
        arena: {
          title: 'Avant de commencer',
          introduction: 'Introduction',
          checkboxLabel: 'J’accepte.',
          links: [],
          buttonLabel: 'Continuer'
        },
        signIn: { checkboxLabel: 'J’accepte.', links: [] }
      }
    })

    const { getByText, queryByRole } = render(Page)
    await waitFor(() => expect(getByText('Contenu des conditions.')).toBeTruthy())

    expect(queryByRole('link', { name: 'Retour à l’arène' })).toBeNull()
    expect(queryByRole('link', { name: 'Politique de confidentialité' })).toBeNull()
  })
})
