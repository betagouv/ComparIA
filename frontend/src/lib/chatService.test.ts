import { describe, expect, it, vi } from 'vitest'
import { getComparison, parseAPIComparison, type APIComparison } from './chatService.svelte'

const streamed = vi.hoisted(() => [] as { url: string; body: Record<string, unknown> }[])

vi.mock('$app/navigation', () => ({ goto: vi.fn() }))
vi.mock('$lib/captcha.svelte', () => ({
  CaptchaError: class extends Error {},
  consumeAltchaToken: async () => 'solved-token'
}))
vi.mock('$lib/fastapi-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/fastapi-client')>()),
  api: {
    async *stream(url: string, body: Record<string, unknown>) {
      streamed.push({ url, body })
    }
  }
}))
vi.mock('svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('svelte')>()),
  createContext: () => [() => [], () => undefined]
}))

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
})

describe('retry', () => {
  it('sends a solved captcha, which the backend requires before calling the models again', async () => {
    streamed.length = 0

    await getComparison('comparison-id').retry()

    expect(streamed).toEqual([
      { url: '/arena/retry/comparison-id', body: { altcha_token: 'solved-token' } }
    ])
  })
})
