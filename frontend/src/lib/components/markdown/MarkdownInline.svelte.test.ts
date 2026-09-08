import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import MarkdownInline from './MarkdownInline.svelte'

const message = 'Lire [**les conditions**](/arene/modalites)'

describe('MarkdownInline', () => {
  it('renders inline markdown', () => {
    const { container } = render(MarkdownInline, { message })

    expect(container.querySelector('a')?.getAttribute('href')).toBe('/arene/modalites')
    expect(container.querySelector('strong')).toBeTruthy()
  })

  it('keeps formatting but no link when allowLinks is false', () => {
    const { container } = render(MarkdownInline, { message, allowLinks: false })

    expect(container.querySelector('a')).toBeNull()
    expect(container.querySelector('strong')?.textContent).toBe('les conditions')
  })
})
