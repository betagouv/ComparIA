import { render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from '../../routes/arene/donnees-personnelles/+page.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/global.svelte', () => ({
  getI18nContext: () => ({ contact: 'contact@example.test' })
}))

describe('Privacy policy page', () => {
  it('does not flash the fallback policy while the configured policy is loading', () => {
    mocks.request.mockReturnValue(new Promise(() => {}))

    const { getByRole, queryByRole } = render(Page)

    expect(getByRole('status').textContent).toContain('Chargement')
    expect(queryByRole('heading', { name: 'Responsable du traitement' })).toBeNull()
    expect(queryByRole('heading', { name: 'Gérer vos choix' })).toBeNull()
    expect(queryByRole('heading', { name: 'Supprimer mon compte' })).toBeNull()
  })

  it('keeps the existing privacy information and Matomo opt-out as the fallback', async () => {
    mocks.request.mockRejectedValue(new Error('Not found'))

    const { container, queryByText } = render(Page)

    await waitFor(() => expect(container.querySelector('#matomo-opt-out')).toBeTruthy())
    expect(queryByText(/doivent encore être fixées/)).toBeNull()
    expect(queryByText(/qualification juridique définitive/)).toBeNull()
  })
})
