import { describe, expect, it } from 'vitest'
import { parseAPIComparison, type APIComparison } from './chatService.svelte'

describe('parseAPIComparison', () => {
  it('marks a persisted incomplete turn as interrupted after a page reload', () => {
    const comparison = {
      id: 'comparison-id',
      turns: [
        {
          id: 'turn-id',
          user_msg: { content: 'hello' },
          llm_msg_a: null,
          llm_msg_b: null,
          choice: null
        }
      ]
    } as unknown as APIComparison

    const parsed = parseAPIComparison(comparison, true)

    expect(parsed.error).toBe('provider_error')
    expect(parsed.turns[0].status).toBe('error')
  })

  it('keeps a newly streamed incomplete turn pending', () => {
    const comparison = {
      id: 'comparison-id',
      turns: [
        {
          id: 'turn-id',
          user_msg: { content: 'hello' },
          llm_msg_a: null,
          llm_msg_b: null,
          choice: null
        }
      ]
    } as unknown as APIComparison

    expect(parseAPIComparison(comparison).turns[0].status).toBe('pending')
  })

  it('shows a turn the user stopped as interrupted, and lets it be voted on', () => {
    const comparison = {
      id: 'comparison-id',
      turns: [
        {
          id: 'turn-id',
          user_msg: { content: 'hello' },
          llm_msg_a: { content: 'Il était une fois', interrupted: true },
          llm_msg_b: { content: 'Bonjour', interrupted: false },
          choice: null
        }
      ]
    } as unknown as APIComparison

    const parsed = parseAPIComparison(comparison, true)

    expect(parsed.error).toBeUndefined()
    expect(parsed.turns[0].status).toBe('interrupted')
    expect(parsed.turns[0].a.status).toBe('interrupted')
    expect(parsed.turns[0].b.status).toBe('complete')
  })

  it('treats a turn stopped before one side answered like any cut-off turn after a reload', () => {
    const comparison = {
      id: 'comparison-id',
      turns: [
        {
          id: 'turn-id',
          user_msg: { content: 'hello' },
          llm_msg_a: { content: 'Il était une fois', interrupted: true },
          llm_msg_b: null,
          choice: null
        }
      ]
    } as unknown as APIComparison

    const parsed = parseAPIComparison(comparison, true)

    expect(parsed.error).toBe('provider_error')
    expect(parsed.turns[0].status).toBe('error')
    expect(parsed.turns[0].a.status).toBe('interrupted')
    expect(parsed.turns[0].b.status).toBe('error')
  })
})
