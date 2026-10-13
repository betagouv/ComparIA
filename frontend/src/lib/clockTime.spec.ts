import { describe, expect, it } from 'vitest'
import { clockTime } from './clockTime'

describe('clockTime', () => {
  const now = new Date(2026, 9, 13, 14, 0)

  it('writes the French hour with an h', () => {
    expect(clockTime(new Date(2026, 9, 13, 15, 40), 'fr', now)).toEqual({
      time: '15 h 40',
      tomorrow: false
    })
    expect(clockTime(new Date(2026, 9, 13, 9, 5), 'fr', now).time).toBe('9 h 05')
  })

  it('writes the English hour with a lowercase am or pm', () => {
    expect(clockTime(new Date(2026, 9, 13, 15, 40), 'en', now).time).toMatch(/^3:40\spm$/)
  })

  it('says when the time falls after midnight', () => {
    expect(clockTime(new Date(2026, 9, 14, 1, 30), 'fr', now)).toEqual({
      time: '1 h 30',
      tomorrow: true
    })
  })
})
