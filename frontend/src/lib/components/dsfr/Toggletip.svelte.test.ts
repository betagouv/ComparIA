import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Toggletip from './Toggletip.svelte'

const props = {
  id: 'why',
  label: 'Pourquoi ?',
  text: 'Pour que compar:IA reste gratuit pour tous.'
}

describe('Toggletip', () => {
  it('opens on a click and says what it holds through its live region', async () => {
    const view = render(Toggletip, props)
    const button = view.getByRole('button', { name: 'Pourquoi ?' })

    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button).toHaveAttribute('aria-controls', 'why')
    expect(view.getByRole('status')).toBeEmptyDOMElement()

    await fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(view.getByRole('status')).toHaveTextContent(
      'Pour que compar:IA reste gratuit pour tous.'
    )

    await fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })

  it('closes on Escape and gives focus back to its button', async () => {
    const view = render(Toggletip, props)
    const button = view.getByRole('button', { name: 'Pourquoi ?' })
    await fireEvent.click(button)

    await fireEvent.keyDown(window, { key: 'Escape' })

    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button).toHaveFocus()
    expect(view.getByRole('status')).toBeEmptyDOMElement()
  })

  it('keeps an Escape meant for it from closing a dialog around it', async () => {
    const view = render(Toggletip, props)
    const button = view.getByRole('button', { name: 'Pourquoi ?' })
    const dialog = vi.fn()
    document.addEventListener('keydown', dialog)
    await fireEvent.click(button)

    await fireEvent.keyDown(button, { key: 'Escape' })

    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(dialog).not.toHaveBeenCalled()
    document.removeEventListener('keydown', dialog)
  })

  it('closes on a click elsewhere', async () => {
    const view = render(Toggletip, props)
    const button = view.getByRole('button', { name: 'Pourquoi ?' })
    await fireEvent.click(button)

    await fireEvent.click(document.body)

    expect(button).toHaveAttribute('aria-expanded', 'false')
  })
})
