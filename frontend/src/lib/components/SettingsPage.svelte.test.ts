import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from '../../routes/arene/parametres/+page.svelte'

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'utilisateur@example.test' } }),
  logout: vi.fn()
}))

vi.mock('$lib/chatService.svelte', () => ({
  getComparisonsContext: () => []
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() }
}))

vi.mock('$lib/consent', () => ({
  withdrawLocalConsent: vi.fn()
}))

describe('Settings page', () => {
  it('groups account actions and legal information into two tabs', async () => {
    const { getByRole, getByLabelText, queryByRole } = render(Page)

    expect(getByRole('heading', { level: 1, name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('tab', { name: 'Compte', selected: true })).toBeTruthy()
    expect(getByLabelText('Adresse électronique')).toBeDisabled()
    expect(getByRole('button', { name: 'Se déconnecter' })).toBeTruthy()
    expect(getByRole('button', { name: 'Exporter mes données' })).toBeTruthy()

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(getByRole('heading', { name: 'Liens utiles' })).toBeTruthy()
    expect(getByRole('link', { name: 'Conditions générales d’utilisation' })).toHaveAttribute(
      'href',
      '/arene/modalites'
    )
    expect(getByRole('link', { name: 'Politique de confidentialité' })).toHaveAttribute(
      'href',
      '/arene/donnees-personnelles'
    )
    expect(queryByRole('link', { name: 'Mentions légales' })).toBeNull()
    expect(queryByRole('heading', { name: 'Profil' })).toBeNull()
  })
})
