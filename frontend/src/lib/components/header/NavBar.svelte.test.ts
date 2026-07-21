import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import NavBar from './NavBar.svelte'

const mocks = vi.hoisted(() => ({
  getComparisonsContext: vi.fn(() => {
    throw new Error('Comparison context is unavailable outside the arena')
  })
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({
    user: { email: 'admin@example.test', role: 'admin' },
    config: {
      access_policy: 'anonymous_first',
      has_custom_logo: false,
      platform_name: 'Plateforme de test'
    }
  }),
  logout: vi.fn()
}))

vi.mock('$lib/chatService.svelte', () => ({
  getComparisonsContext: mocks.getComparisonsContext
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { getUrl: (path: string) => path }
}))

vi.mock('$lib/global.svelte', () => ({
  LOCALES: [{ code: 'fr', short: 'FR', long: 'FR - Français', host: 'localhost:5173' }],
  getVotesContext: () => ({ count: 0, objective: 100 })
}))

describe('NavBar admin', () => {
  it('renders the global legal menu without requiring the arena comparison context', async () => {
    const { container, getByRole, queryByRole } = render(NavBar, { navLinks: [], isAdmin: true })

    expect(container.textContent).not.toContain('admin@example.test')
    expect(getByRole('link', { name: 'Paramètres' })).toBeTruthy()
    expect(getByRole('button', { name: 'Se déconnecter' })).toBeTruthy()
    const legalMenuButton = getByRole('button', { name: 'Informations légales' })
    expect(legalMenuButton).toHaveTextContent('Légal')
    await fireEvent.click(legalMenuButton)

    expect(getByRole('link', { name: 'Données personnelles et confidentialité' })).toBeTruthy()
    expect(getByRole('link', { name: 'Conditions générales d’utilisation' })).toBeTruthy()
    expect(getByRole('link', { name: 'Accessibilité : non conforme' }).getAttribute('href')).toBe(
      '/arene/accessibilite'
    )
    expect(getByRole('link', { name: 'Écoconception' }).getAttribute('href')).toBe(
      '/arene/ecoconception'
    )
    expect(queryByRole('link', { name: 'Mentions légales' })).toBeNull()
    expect(mocks.getComparisonsContext).not.toHaveBeenCalled()
  })
})
