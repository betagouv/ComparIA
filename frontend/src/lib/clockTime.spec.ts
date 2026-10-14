import { describe, expect, it } from 'vitest'
import { clockTime } from './clockTime'

describe('clockTime', () => {
  const now = new Date(2026, 9, 13, 14, 0)

  it('writes the French hour with an h, on one line', () => {
    expect(clockTime(new Date(2026, 9, 13, 15, 40), 'fr', now)).toEqual({
      time: '15\u00a0h\u00a040',
      tomorrow: false
    })
    expect(clockTime(new Date(2026, 9, 13, 9, 5), 'fr', now).time).toBe('9\u00a0h\u00a005')
  })

  it('writes the English hour with a lowercase am or pm', () => {
    expect(clockTime(new Date(2026, 9, 13, 15, 40), 'en', now).time).toBe('3:40\u00a0pm')
  })

  it('says when the time falls after midnight', () => {
    expect(clockTime(new Date(2026, 9, 14, 1, 30), 'fr', now)).toEqual({
      time: '1\u00a0h\u00a030',
      tomorrow: true
    })
  })
})
