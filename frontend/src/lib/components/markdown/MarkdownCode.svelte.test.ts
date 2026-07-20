import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import MarkdownCode from './MarkdownCode.svelte'

describe('MarkdownCode document variant', () => {
  it('uses compact block-level document styles without heading anchors', () => {
    const { container, getByRole } = render(MarkdownCode, {
      message: 'Introduction\n\n## Section\n\nContenu',
      variant: 'document'
    })

    const document = container.querySelector('.md.document')
    const heading = getByRole('heading', { name: 'Section' })

    expect(document).toBeTruthy()
    expect(document?.classList.contains('document')).toBe(true)
    expect(heading.querySelector('.md-header-anchor')).toBeNull()
  })
})
