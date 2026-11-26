import CookieBanner from '$lib/components/CookieBanner.svelte'
import type { CookieChoice } from '$lib/cookieConsent'
import { fireEvent, render, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

const text = {
  title: 'Audience measurement',
  description: 'We would like to count visits without identifying you.'
}

function renderBanner(props: { choice?: CookieChoice | null; onClose?: () => void } = {}) {
  const onChoice = vi.fn()
  const result = render(CookieBanner, { text, onChoice, ...props })
  return { ...result, onChoice }
}

describe('CookieBanner', () => {
  it('asks one question, with refusing as easy to find as accepting', () => {
    const { getByRole, getAllByRole, getByText } = renderBanner()

    expect(getByRole('region', { name: text.title })).toBeInTheDocument()
    expect(getByText(text.description)).toBeInTheDocument()
    const accept = getByRole('button', { name: 'Accepter' })
    const refuse = getByRole('button', { name: 'Refuser' })
    expect(refuse.className).toBe(accept.className)
    expect(getAllByRole('button')).toHaveLength(2)
  })

  it('links to the privacy policy', () => {
    const { getByRole } = renderBanner()
    expect(getByRole('link', { name: /Politique de confidentialité/ })).toHaveAttribute(
      'href',
      expect.stringContaining('/privacy_policy')
    )
  })

  it('answers in one click', async () => {
    const { getByRole, onChoice } = renderBanner()

    await fireEvent.click(getByRole('button', { name: 'Accepter' }))
    expect(onChoice).toHaveBeenLastCalledWith({ measurement: true })

    await fireEvent.click(getByRole('button', { name: 'Refuser' }))
    expect(onChoice).toHaveBeenLastCalledWith({ measurement: false })
  })

  it.each([
    [true, 'Votre réponse actuelle : oui'],
    [false, 'Votre réponse actuelle : non']
  ])('shows an answer of %s when reopened', (measurement, current) => {
    const { getByText } = renderBanner({ choice: { measurement }, onClose: vi.fn() })
    expect(getByText(current)).toBeInTheDocument()
  })

  it('takes focus when reopened, and can be closed', async () => {
    const onClose = vi.fn()
    const { getByRole } = renderBanner({ choice: { measurement: true }, onClose })

    await vi.waitFor(() => expect(getByRole('heading', { name: text.title })).toHaveFocus())

    await fireEvent.keyDown(getByRole('button', { name: 'Refuser' }), { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    await fireEvent.click(getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('previews without adding a landmark to the page', () => {
    const { getByRole, queryByRole } = render(CookieBanner, { text, preview: true })

    expect(queryByRole('region')).toBeNull()
    expect(getByRole('heading', { name: text.title })).toBeInTheDocument()
  })

  it('opens the privacy policy in a new tab from the preview, keeping the admin form', () => {
    const { getByRole } = render(CookieBanner, { text, preview: true })
    const link = getByRole('link', { name: /Politique de confidentialité/ })

    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener')
  })

  it('does not take focus the first time it asks', async () => {
    const { getByRole } = renderBanner()
    await new Promise((r) => setTimeout(r))
    expect(within(getByRole('region')).queryByRole('heading')).not.toHaveFocus()
    expect(document.body).toHaveFocus()
  })
})
