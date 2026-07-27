import { describe, expect, it } from 'vitest'
import { renderInlineMarkdown } from './inline'

describe('renderInlineMarkdown', () => {
  it('renders inline formatting and links', () => {
    const html = renderInlineMarkdown(
      '**Important**, *à lire* sur [la page dédiée](https://example.test/conditions).'
    )

    expect(html).toContain('<strong>Important</strong>')
    expect(html).toContain('<em>à lire</em>')
    expect(html).toContain('href="https://example.test/conditions"')
  })

  it('drops unsafe markup', () => {
    expect(
      renderInlineMarkdown('[Piège](javascript:alert(1)) <script>alert(1)</script>')
    ).not.toMatch(/javascript:|<script/i)
  })

  it('keeps link text only when links are not allowed', () => {
    expect(renderInlineMarkdown('Lire [les conditions](/arene/modalites)', false)).toBe(
      'Lire les conditions'
    )
    expect(renderInlineMarkdown('Lire <a href="https://evil.test">ici</a>', false)).toBe('Lire ici')
    expect(renderInlineMarkdown('Lire [**les conditions**](/arene/modalites)', false)).toBe(
      'Lire <strong>les conditions</strong>'
    )
  })
})
