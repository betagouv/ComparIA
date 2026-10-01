/**
 * DSFR italicises input placeholders, and the arena's prompt textarea has one,
 * so the browser fetched Marianne-Regular_Italic.woff2 (44 KB) for text nobody
 * reads in italic. app.css overrides it; a DSFR upgrade could quietly undo that.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = join(import.meta.dirname, '..')

/** Every `font-style` set on a placeholder selector, in cascade order. */
function placeholderStyles(css: string): { selectors: string[]; style: string }[] {
  const rules = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/@import[^;]*;/g, '')
  return [...rules.matchAll(/([^{};]*::placeholder[^{}]*)\{([^}]*)\}/g)].flatMap(
    ([, selector, body]) => {
      const style = body.match(/font-style:\s*([a-z]+)/)?.[1]
      return style ? [{ selectors: selector.split(',').map((s) => s.trim()), style }] : []
    }
  )
}

describe('placeholders', () => {
  const app = readFileSync(join(root, 'css/app.css'), 'utf8')
  const dsfr = readFileSync(join(root, '..', 'node_modules/@gouvfr/dsfr/dist/dsfr.min.css'), 'utf8')

  it('keeps every placeholder DSFR italicises upright', () => {
    const italic = placeholderStyles(dsfr).filter(({ style }) => style === 'italic')
    const upright = placeholderStyles(app).filter(({ style }) => style === 'normal')

    // Same selector, so same specificity; app.css wins because it comes after the import.
    expect(italic.length).toBeGreaterThan(0)
    for (const { selectors } of italic) {
      for (const selector of selectors) {
        expect(
          upright.some((rule) => rule.selectors.includes(selector)),
          selector
        ).toBe(true)
      }
    }
  })

  it('places the override after the DSFR import', () => {
    expect(app.indexOf("@import '@gouvfr/dsfr/dist/dsfr.min.css'")).toBeLessThan(
      app.indexOf('::placeholder')
    )
  })
})
