import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import LegalMenu from './LegalMenu.svelte'

// The menu reads its links from the consent module, which pulls in the api client.
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))

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
    const trigger = getByRole('button', { name: /Légal/ })

    await fireEvent.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')

    await fireEvent.click(document.body)
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
  })

  it('closes on escape from the trigger and takes focus back', async () => {
    const { getByRole } = render(LegalMenu, { id: 'legal-menu-desktop' })
    const trigger = getByRole('button', { name: /Légal/ })

    await fireEvent.click(trigger)
    getByRole('link', { name: 'Écoconception' }).focus()
    await fireEvent.keyDown(window, { key: 'Escape' })

    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(trigger)

    await fireEvent.click(trigger)
    trigger.focus()
    await fireEvent.keyDown(window, { key: 'Escape' })
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
  })

  it('keeps the desktop and mobile copies apart', async () => {
    render(LegalMenu, { id: 'legal-menu-desktop' })
    render(LegalMenu, { id: 'legal-menu-mobile' })

    const desktop = document.getElementById('legal-menu-desktop-trigger')!
    const mobile = document.getElementById('legal-menu-mobile-trigger')!

    await fireEvent.click(desktop)

    expect(desktop.getAttribute('aria-expanded')).toBe('true')
    expect(mobile.getAttribute('aria-expanded')).toBe('false')
  })
})
