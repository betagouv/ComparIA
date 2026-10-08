import { describe, expect, it } from 'vitest'
import { MCP_PRESETS, toKey, uniqueKey } from './presets'

describe('toKey', () => {
  it('turns a French label into a plain key', () => {
    expect(toKey('Données publiques')).toBe('donnees_publiques')
    expect(toKey("  L'outil : v2 ! ")).toBe('l_outil_v2')
  })
})

describe('uniqueKey', () => {
  it('keeps a free key and numbers a taken one', () => {
    expect(uniqueKey('deepwiki', ['context7'])).toBe('deepwiki')
    expect(uniqueKey('deepwiki', ['deepwiki', 'deepwiki_2'])).toBe('deepwiki_3')
  })

  it('falls back on a default when the label had nothing to keep', () => {
    expect(uniqueKey(toKey('!!!'), [])).toBe('outil')
  })
})

describe('MCP_PRESETS', () => {
  it('never offers the same server or key twice', () => {
    expect(new Set(MCP_PRESETS.map((p) => p.url)).size).toBe(MCP_PRESETS.length)
    expect(new Set(MCP_PRESETS.map((p) => p.key)).size).toBe(MCP_PRESETS.length)
  })
})
