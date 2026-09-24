import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('informational badge theme', () => {
  it('uses the semantic info palette independently from platform branding', () => {
    const source = readFileSync(new URL('./Badge.svelte', import.meta.url), 'utf8')

    expect(source).toContain('background-color: var(--info-950-100)')
    expect(source).toContain('color: var(--info-425-625)')
    expect(source).not.toContain('background-color: var(--brand-primary)')
  })
})
