import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import DownloadDataButton from './DownloadDataButton.svelte'

describe('DownloadDataButton', () => {
  // An anchor with `download` saves the current page next to the CSV.
  it('is a plain button that only runs the handler', async () => {
    const onclick = vi.fn()
    const { getByRole } = render(DownloadDataButton, { onclick })

    const button = getByRole('button')
    expect(button.getAttribute('type')).toBe('button')
    expect(button.hasAttribute('download')).toBe(false)

    await fireEvent.click(button)
    expect(onclick).toHaveBeenCalledOnce()
  })
})
