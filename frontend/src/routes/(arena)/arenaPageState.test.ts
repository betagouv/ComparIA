import { describe, expect, it } from 'vitest'
import { shouldShowInitialPrompt } from './arenaPageState'

describe('shouldShowInitialPrompt', () => {
  it('keeps the optimistic prompt mounted between the init and add stream events', () => {
    expect(shouldShowInitialPrompt('comparison-id', { turns: [] } as never)).toBe(true)
  })

  it('hands off to the chat once the first real turn exists', () => {
    expect(shouldShowInitialPrompt('comparison-id', { turns: [{ id: 'turn-id' }] } as never)).toBe(
      false
    )
  })
})
