import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import LegalMenu from './LegalMenu.svelte'

// The menu reads its links from the consent module, which pulls in the api client.
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))

const trigger = (id: string) =>
  document.querySelector<HTMLButtonElement>(`[aria-controls="dropdown-${id}"]`)!

describe('LegalMenu', () => {
  it('lists the public legal pages', async () => {
    const { getByRole } = render(LegalMenu, { id: 'legal-menu-desktop' })

    await fireEvent.click(getByRole('button', { name: /Légal/ }))

    expect(getByRole('link', { name: 'Politique de confidentialité' }).getAttribute('href')).toBe(
      '/arene/donnees-personnelles'
    )
    expect(
      getByRole('link', { name: 'Conditions générales d’utilisation' }).getAttribute('href')
    ).toBe('/arene/modalites')
    expect(getByRole('link', { name: /Accessibilité/ }).getAttribute('href')).toBe(
      '/arene/accessibilite'
    )
    expect(getByRole('link', { name: 'Écoconception' }).getAttribute('href')).toBe(
      '/arene/ecoconception'
    )
  })

  it('closes on a click outside', async () => {
    const { getByRole } = render(LegalMenu, { id: 'legal-menu-desktop' })
    const button = getByRole('button', { name: /Légal/ })

    await fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('true')

    await fireEvent.pointerDown(document.body)
    expect(button.getAttribute('aria-expanded')).toBe('false')
  })

  it('closes on escape from inside the menu and takes focus back', async () => {
    const { getByRole } = render(LegalMenu, { id: 'legal-menu-desktop' })
    const button = getByRole('button', { name: /Légal/ })

    await fireEvent.click(button)
    await fireEvent.keyDown(getByRole('link', { name: 'Écoconception' }), { key: 'Escape' })

    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(button)
  })

  it('keeps the desktop and mobile copies apart', async () => {
    render(LegalMenu, { id: 'legal-menu-desktop' })
    render(LegalMenu, { id: 'legal-menu-mobile' })

    const desktop = trigger('legal-menu-desktop')
    const mobile = trigger('legal-menu-mobile')

    await fireEvent.click(desktop)

    expect(desktop.getAttribute('aria-expanded')).toBe('true')
    expect(mobile.getAttribute('aria-expanded')).toBe('false')
  })
})
