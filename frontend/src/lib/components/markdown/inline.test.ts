import { describe, expect, it } from 'vitest'
import { renderInlineMarkdown } from './inline'

describe('inline Markdown', () => {
  it('renders useful formatting and safe links', () => {
    const html = renderInlineMarkdown(
      '**Important**, *à lire* sur [la page dédiée](https://example.test/conditions).'
    )

    expect(html).toContain('<strong>Important</strong>')
    expect(html).toContain('<em>à lire</em>')
    expect(html).toContain('href="https://example.test/conditions"')
  })

  it('removes unsafe HTML and can neutralize links inside buttons', () => {
    expect(renderInlineMarkdown('[Piège](javascript:alert(1)) <script>alert(1)</script>')).not.toMatch(
      /javascript:|<script/i
    )
    expect(renderInlineMarkdown('Lire [les conditions](/arene/modalites)', false)).toBe(
      'Lire les conditions'
    )
  })
})
