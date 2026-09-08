import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import MarkdownCode from './MarkdownCode.svelte'

describe('MarkdownCode', () => {
  it('keeps the chat variant by default', () => {
    const { container } = render(MarkdownCode, { message: '# Titre' })

    expect(container.querySelector('.md.document')).toBeNull()
    expect(container.querySelector('h1')).toBeTruthy()
  })

  it('normalizes headings in the document variant', () => {
    const { container } = render(MarkdownCode, {
      message: '# Titre\n\n#### Section\n\nContenu',
      variant: 'document'
    })

    expect(container.querySelector('.md.document')).toBeTruthy()
    expect(container.querySelector('h1')).toBeNull()
    expect(Array.from(container.querySelectorAll('h2, h3')).map((el) => el.tagName)).toEqual([
      'H2',
      'H3'
    ])
  })
})
