import { render } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Modal from './Modal.svelte'

// Stands in for DSFR, which conceals an open modal on Escape from a capturing
// listener on the document.
const dsfrEscape = vi.fn()
const listen = (event: KeyboardEvent) => event.key === 'Escape' && dsfrEscape()
document.documentElement.addEventListener('keydown', listen, { capture: true })

function pressEscapeOn(locked: boolean) {
  const { container } = render(Modal, { id: 'm', titleId: 't', locked })
  container.querySelector('dialog')!.classList.add('fr-modal--opened')
  document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
}

describe('Modal', () => {
  afterEach(() => dsfrEscape.mockClear())

  it('lets DSFR close an ordinary modal on Escape', () => {
    pressEscapeOn(false)
    expect(dsfrEscape).toHaveBeenCalled()
  })

  it('keeps a locked modal open on Escape', () => {
    pressEscapeOn(true)
    expect(dsfrEscape).not.toHaveBeenCalled()
  })
})
