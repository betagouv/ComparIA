import { describe, expect, it } from 'vitest'
import { formatLanguage } from './languageName'

describe('formatLanguage', () => {
  it.each([
    ['fr', 'da', 'fransk'],
    ['en', 'da', 'engelsk'],
    ['da', 'en', 'Danish'],
    ['en', 'fr', 'anglais']
  ] as const)('names %s for a %s reader', (code, reader, name) => {
    expect(formatLanguage(code, reader)).toBe(name)
  })

  it('falls back to the code for a value it cannot name', () => {
    expect(formatLanguage('not a code', 'en')).toBe('not a code')
  })
})
