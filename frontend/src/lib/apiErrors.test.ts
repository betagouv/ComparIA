import { describe, expect, it } from 'vitest'
import { arenaErrorMessage, isArenaErrorKey } from './apiErrors'

describe('arena errors', () => {
  it('explains a model that can no longer be picked', () => {
    expect(isArenaErrorKey('model_unavailable')).toBe(true)
    expect(arenaErrorMessage('model_unavailable')).toMatch(/reload/i)
  })
  it('explains a mode that is no longer on offer', () => {
    expect(isArenaErrorKey('mode_unavailable')).toBe(true)
    expect(arenaErrorMessage('mode_unavailable')).toMatch(/default mode/i)
  })
})
