import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from '../../routes/arene/parametres/+page.svelte'

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'utilisateur@example.test' } })
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() }
}))

vi.mock('$lib/consent', () => ({
  withdrawLocalConsent: vi.fn()
}))

describe('Settings page', () => {
  it('places account deletion in the account settings', () => {
    const { getByRole, getByLabelText } = render(Page)

    expect(getByRole('heading', { level: 1, name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('heading', { name: 'Supprimer mon compte' })).toBeTruthy()
    expect(getByLabelText(/Confirmez votre adresse électronique/)).toBeTruthy()
  })
})
