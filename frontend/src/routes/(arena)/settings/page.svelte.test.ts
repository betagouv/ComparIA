import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import { PRIVACY_POLICY_PATH, TERMS_PATH, ACCESSIBILITY_PATH, ECODESIGN_PATH } from '$lib/consent'

const request = vi.fn()

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'personne@example.org' } }),
  logout: vi.fn()
}))

vi.mock('$lib/chatService.svelte', () => ({ getComparisonsContext: () => [] }))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: (...args: unknown[]) => request(...args) }
}))

describe('Settings page', () => {
  it('splits the account actions from the legal information', async () => {
    const { container, getByRole, getByLabelText } = render(Page)

    expect(getByRole('heading', { level: 1, name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('tab', { name: 'Compte' }).getAttribute('aria-selected')).toBe('true')
    expect(getByLabelText('Adresse électronique').hasAttribute('disabled')).toBe(true)
    expect(getByRole('button', { name: 'Se déconnecter' })).toBeTruthy()
    expect(getByRole('button', { name: 'Exporter mes données' })).toBeTruthy()

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(getByRole('heading', { name: 'Liens utiles' })).toBeTruthy()
    expect(
      getByRole('link', { name: 'Conditions générales d’utilisation' }).getAttribute('href')
    ).toBe(TERMS_PATH)
    expect(getByRole('link', { name: 'Politique de confidentialité' }).getAttribute('href')).toBe(
      PRIVACY_POLICY_PATH
    )
    expect(getByRole('link', { name: /Accessibilité/ }).getAttribute('href')).toBe(
      ACCESSIBILITY_PATH
    )
    expect(getByRole('link', { name: 'Écoconception' }).getAttribute('href')).toBe(ECODESIGN_PATH)
    // Tabs keeps every panel in the DOM and hides the inactive ones through
    // the DSFR styles, so the selected class is what separates them here.
    expect(container.querySelector('#tab-about-panel')).toHaveClass('fr-tabs__panel--selected')
    expect(container.querySelector('#tab-account-panel')).not.toHaveClass(
      'fr-tabs__panel--selected'
    )
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
