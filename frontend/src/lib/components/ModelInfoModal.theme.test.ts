import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('model information colours', () => {
  it('keeps technical metadata icons informational rather than branded', () => {
    const source = readFileSync(new URL('./ModelInfoModal.svelte', import.meta.url), 'utf8')

    expect(source).toContain("iconClass = 'text-info'")
    expect(source).toContain('iconClass="text-info"')
  })
})
