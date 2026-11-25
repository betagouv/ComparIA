import CookieBanner from '$lib/components/CookieBanner.svelte'
import type { CookieChoice } from '$lib/cookieConsent'
import { fireEvent, render, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

const text = {
  title: 'Cookies on this site',
  description: 'We ask before setting cookies we do not need.',
  audience_measurement_label: 'Audience measurement',
  audience_measurement_description: 'Counts visits anonymously.',
  remembered_settings_label: 'Remembered settings',
  remembered_settings_description: 'Keeps your language and theme.'
}

function renderBanner(props: { choice?: CookieChoice | null; onClose?: () => void } = {}) {
  const onChoice = vi.fn()
  const result = render(CookieBanner, { text, onChoice, ...props })
  return { ...result, onChoice }
}

describe('CookieBanner', () => {
  it('shows the text and three buttons of equal weight', () => {
    const { getByRole, getByText } = renderBanner()

    expect(getByRole('region', { name: text.title })).toBeInTheDocument()
    expect(getByText(text.description)).toBeInTheDocument()
    const buttons = ['Tout accepter', 'Tout refuser', 'Choisir'].map((name) =>
      getByRole('button', { name })
    )
    const classes = buttons.map((button) => button.className)
    expect(new Set(classes).size).toBe(1)
  })

  it('links to the privacy policy', () => {
    const { getByRole } = renderBanner()
    expect(getByRole('link', { name: /Politique de confidentialité/ })).toHaveAttribute(
      'href',
      expect.stringContaining('/privacy_policy')
    )
  })

  it('accepts or refuses everything in one click', async () => {
    const { getByRole, onChoice } = renderBanner()

    await fireEvent.click(getByRole('button', { name: 'Tout accepter' }))
    expect(onChoice).toHaveBeenLastCalledWith({ measurement: true, preferences: true })

    await fireEvent.click(getByRole('button', { name: 'Tout refuser' }))
    expect(onChoice).toHaveBeenLastCalledWith({ measurement: false, preferences: false })
  })

  it('lets people pick each kind of cookie, none ticked at first', async () => {
    const { getByRole, getByText, onChoice } = renderBanner()
    const choose = getByRole('button', { name: 'Choisir' })
    expect(choose).toHaveAttribute('aria-expanded', 'false')

    await fireEvent.click(choose)

    expect(choose).toHaveAttribute('aria-expanded', 'true')
    const measurement = getByRole('checkbox', { name: /Audience measurement/ })
    const settings = getByRole('checkbox', { name: /Remembered settings/ })
    expect(measurement).not.toBeChecked()
    expect(settings).not.toBeChecked()
    expect(getByText(text.audience_measurement_description)).toBeInTheDocument()
    expect(getByText(text.remembered_settings_description)).toBeInTheDocument()
    await vi.waitFor(() => expect(measurement).toHaveFocus())

    await fireEvent.click(settings)
    await fireEvent.click(getByRole('button', { name: 'Enregistrer mes choix' }))
    expect(onChoice).toHaveBeenCalledWith({ measurement: false, preferences: true })
  })

  it('closes the choice panel on Escape and gives focus back to Choose', async () => {
    const { getByRole, queryByRole } = renderBanner()
    const choose = getByRole('button', { name: 'Choisir' })
    await fireEvent.click(choose)

    await fireEvent.keyDown(getByRole('checkbox', { name: /Audience measurement/ }), {
      key: 'Escape'
    })

    expect(choose).toHaveAttribute('aria-expanded', 'false')
    expect(queryByRole('checkbox', { name: /Audience measurement/ })).toBeNull()
    expect(choose).toHaveFocus()
  })

  it('shows the current choice when reopened, and can be closed', async () => {
    const onClose = vi.fn()
    const { getByRole } = renderBanner({
      choice: { measurement: true, preferences: false },
      onClose
    })

    expect(getByRole('checkbox', { name: /Audience measurement/ })).toBeChecked()
    expect(getByRole('checkbox', { name: /Remembered settings/ })).not.toBeChecked()
    await vi.waitFor(() => expect(getByRole('heading', { name: text.title })).toHaveFocus())

    await fireEvent.keyDown(getByRole('region'), { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    await fireEvent.click(getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('does not take focus the first time it asks', async () => {
    const { getByRole } = renderBanner()
    await new Promise((r) => setTimeout(r))
    expect(within(getByRole('region')).queryByRole('heading')).not.toHaveFocus()
    expect(document.body).toHaveFocus()
  })
})
