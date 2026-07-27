import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const request = vi.fn()

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'personne@example.org' } }),
  logout: vi.fn()
}))

vi.mock('$lib/chatService.svelte', () => ({ getComparisonsContext: () => [] }))
vi.mock('$lib/consent', () => ({ resetConsent: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: (...args: unknown[]) => request(...args) }
}))

describe('Settings page', () => {
  it('splits the account actions from the legal information', async () => {
    const { getByRole, getByLabelText, queryByRole } = render(Page)

    expect(getByRole('heading', { level: 1, name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('tab', { name: 'Compte' }).getAttribute('aria-selected')).toBe('true')
    expect(getByLabelText('Adresse électronique').hasAttribute('disabled')).toBe(true)
    expect(getByRole('button', { name: 'Se déconnecter' })).toBeTruthy()
    expect(getByRole('button', { name: 'Exporter mes données' })).toBeTruthy()

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(getByRole('heading', { name: 'Liens utiles' })).toBeTruthy()
    expect(
      getByRole('link', { name: 'Conditions générales d’utilisation' }).getAttribute('href')
    ).toBe('/modalites')
    expect(queryByRole('button', { name: 'Exporter mes données' })).toBeNull()
  })

  it('asks the backend for the export rather than building it in the page', async () => {
    request.mockResolvedValue({ schema_version: 1, conversations: [], consents: [] })
    const { getByRole } = render(Page)

    await fireEvent.click(getByRole('button', { name: 'Exporter mes données' }))

    await waitFor(() => expect(request).toHaveBeenCalledWith('/auth/me/export'))
  })

  it('only enables the erasure once the account address is retyped', async () => {
    const { container } = render(Page)

    const modal = container.querySelector('#account-erasure-modal')!
    const confirm = () =>
      [...modal.querySelectorAll('button')].find(
        (button) => button.textContent?.trim() === 'Supprimer mon compte'
      )!
    expect(confirm().disabled).toBe(true)
    expect(modal.textContent).toContain('personne@example.org')

    const field = modal.querySelector('#account-erasure-email')!
    await fireEvent.input(field, { target: { value: ' Personne@example.org ' } })

    await waitFor(() => expect(confirm().disabled).toBe(false))
  })
})
