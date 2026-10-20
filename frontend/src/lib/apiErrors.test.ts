import { describe, expect, it } from 'vitest'
import { arenaErrorMessage, isArenaErrorKey } from './apiErrors'

describe('arena errors', () => {
  it('explains a model that can no longer be picked', () => {
    expect(isArenaErrorKey('model_unavailable')).toBe(true)
    expect(arenaErrorMessage('model_unavailable')).toMatch(/recharge/i)
  })
})
