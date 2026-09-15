import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('reveal impact summary layout', () => {
  it('fits the three impact cards on one standard desktop row', () => {
    const source = readFileSync(new URL('./RevealCard.svelte', import.meta.url), 'utf8')

    expect(source).toContain('gap-2 xl:grid-cols-3 md:grid-cols-1 sm:grid-cols-2 grid')
    expect(source).not.toContain('2xl:grid-cols-3 xl:grid-cols-2')
  })

  it('keeps model metadata colours semantic rather than branded', () => {
    const source = readFileSync(new URL('./RevealCard.svelte', import.meta.url), 'utf8')

    expect(source).toContain("iconClass={'iconClass' in card ? card.iconClass : 'text-info'}")
    expect(source.match(/iconClass="text-info"/g)).toHaveLength(3)
  })
})
