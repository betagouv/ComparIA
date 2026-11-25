import { ACCESSIBILITY_PATH, ECODESIGN_PATH, PRIVACY_POLICY_PATH, TERMS_PATH } from '$lib/consent'
import ContextWrapper from '$lib/testing/ContextWrapper.svelte'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LegalMenu from './LegalMenu.svelte'

// The menu reads its links from the consent module, which pulls in the api client.
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))

const cookieConsent = vi.hoisted(() => ({
  enabled: false,
  openedFrom: null as Element | null,
  reopen() {
    cookieConsent.openedFrom = document.activeElement
  }
}))
vi.mock('$lib/stores/cookieConsent.svelte', () => ({
  getCookieConsentContext: () => cookieConsent
}))

beforeEach(() => {
  cookieConsent.enabled = false
  cookieConsent.openedFrom = null
})

function getWrappedComponent(
  id: string = 'legal-menu-desktop',
  props: Record<string, unknown> = {}
) {
  return render(ContextWrapper, {
    props: {
      Component: LegalMenu,
      props: { id, ...props }
    }
  })
}

const trigger = (id: string) =>
  document.querySelector<HTMLButtonElement>(`[aria-controls="dropdown-${id}"]`)!

describe('LegalMenu', () => {
  it('lists the public legal pages', async () => {
    const { getByRole } = getWrappedComponent()

    await fireEvent.click(getByRole('button', { name: /Légal/ }))

    expect(getByRole('link', { name: 'Politique de confidentialité' }).getAttribute('href')).toBe(
      PRIVACY_POLICY_PATH
    )
    expect(
      getByRole('link', { name: 'Conditions générales d’utilisation' }).getAttribute('href')
    ).toBe(TERMS_PATH)
    expect(getByRole('link', { name: /Accessibilité/ }).getAttribute('href')).toBe(
      ACCESSIBILITY_PATH
    )
    expect(getByRole('link', { name: 'Écoconception' }).getAttribute('href')).toBe(ECODESIGN_PATH)
  })

  it('closes on a click outside', async () => {
    const { getByRole } = getWrappedComponent()
    const button = getByRole('button', { name: /Légal/ })

    await fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('true')

    await fireEvent.pointerDown(document.body)
    expect(button.getAttribute('aria-expanded')).toBe('false')
  })

  it('closes on escape from inside the menu and takes focus back', async () => {
    const { getByRole } = getWrappedComponent()
    const button = getByRole('button', { name: /Légal/ })

    await fireEvent.click(button)
    await fireEvent.keyDown(getByRole('link', { name: 'Écoconception' }), { key: 'Escape' })

    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(button)
  })

  it('keeps the desktop and mobile copies apart', async () => {
    getWrappedComponent()
    getWrappedComponent('legal-menu-mobile')

    const desktop = trigger('legal-menu-desktop')
    const mobile = trigger('legal-menu-mobile')

    await fireEvent.click(desktop)

    expect(desktop.getAttribute('aria-expanded')).toBe('true')
    expect(mobile.getAttribute('aria-expanded')).toBe('false')
  })

  it('has no cookies entry while the banner is off', async () => {
    const { getByRole, queryByRole } = getWrappedComponent()

    await fireEvent.click(getByRole('button', { name: /Légal/ }))

    expect(queryByRole('button', { name: 'Cookies' })).toBeNull()
  })

  it('reopens the banner from the menu and leaves focus on the menu button', async () => {
    cookieConsent.enabled = true
    const { getByRole } = getWrappedComponent()
    const button = getByRole('button', { name: /Légal/ })

    await fireEvent.click(button)
    const cookies = getByRole('button', { name: 'Cookies' })
    expect(cookies.closest('li')).toHaveClass('fr-sidemenu__item')
    await fireEvent.click(cookies)

    await waitFor(() => expect(cookieConsent.openedFrom).toBe(button))
    expect(button.getAttribute('aria-expanded')).toBe('false')
  })

  it('reaches the cookies entry with the arrow keys', async () => {
    cookieConsent.enabled = true
    const { getByRole } = getWrappedComponent()

    await fireEvent.click(getByRole('button', { name: /Légal/ }))
    await fireEvent.keyDown(getByRole('link', { name: 'Écoconception' }), { key: 'End' })

    expect(document.activeElement).toBe(getByRole('button', { name: 'Cookies' }))
  })

  it('closes the mobile menu it sits in', async () => {
    cookieConsent.enabled = true
    const { getByRole } = getWrappedComponent('legal-menu-mobile', { modalId: 'fr-modal-menu' })

    await fireEvent.click(getByRole('button', { name: /Légal/ }))
    const cookies = getByRole('button', { name: 'Cookies' })

    expect(cookies.getAttribute('aria-controls')).toBe('fr-modal-menu')
    expect(cookies.hasAttribute('data-fr-js-modal-button')).toBe(true)
  })
})
