import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('conversation history theme', () => {
  it('uses the instance palette for the chosen model badge', () => {
    const source = readFileSync(new URL('./History.svelte', import.meta.url), 'utf8')

    expect(source).toContain("'b-primary bg-light-primary': chosen")
    expect(source).not.toContain('#E8EDFF')
  })
})
