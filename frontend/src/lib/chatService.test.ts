import { describe, expect, it, vi } from 'vitest'
import {
  getComparison,
  parseAPIComparison,
  type APIComparison,
  type Comparison
} from './chatService.svelte'
import { ValidationError } from './fastapi-client'

const streamed = vi.hoisted(() => [] as { url: string; body: Record<string, unknown> }[])
const arena = vi.hoisted(() => ({
  comparisons: [] as unknown[],
  refusal: undefined as Error | undefined
}))

vi.mock('$app/navigation', () => ({ goto: vi.fn() }))
vi.mock('$lib/captcha.svelte', () => ({
  CaptchaError: class extends Error {},
  consumeAltchaToken: async () => 'solved-token'
}))
vi.mock('$lib/fastapi-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/fastapi-client')>()),
  api: {
    // eslint-disable-next-line require-yield
    async *stream(url: string, body: Record<string, unknown>) {
      if (arena.refusal) throw arena.refusal
      streamed.push({ url, body })
    }
  }
}))
vi.mock('svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('svelte')>()),
  createContext: () => [() => arena.comparisons, () => undefined]
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

  it('keeps the Retry button when the retry is refused before it starts', async () => {
    const comparison = {
      id: 'failed-id',
      error: 'provider_error',
      turns: [{ id: 'turn-id', status: 'error', a: {}, b: {} }]
    } as unknown as Comparison
    arena.comparisons = [comparison]
    arena.refusal = Object.assign(new ValidationError('rate_limited'), {
      status: 429,
      detail: 'rate_limited'
    })

    const chat = getComparison('failed-id')
    const sent = await chat.retry()

    arena.refusal = undefined
    arena.comparisons = []
    expect(sent).toBe(false)
    expect(chat.promptError).toBeTruthy()
    // The Retry button shows while the turn is in error and the comparison
    // still says why.
    expect(comparison.error).toBe('provider_error')
    expect(comparison.turns[0].status).toBe('error')
  })
})

describe('a refusal on an allowance', () => {
  const limit = {
    scope: 'network' as const,
    resets_at: '2026-10-13T13:40:00Z',
    resets_in: 4210,
    llm_ids: []
  }

  it('pauses the send area instead of showing an input error, and leaves the reveal open', async () => {
    const comparison = {
      id: 'voted-id',
      turns: [{ id: 'turn-id', status: 'complete', choice: 'a_better', a: {}, b: {} }]
    } as unknown as Comparison
    arena.comparisons = [comparison]
    arena.refusal = Object.assign(new ValidationError('allowance_spent'), {
      status: 429,
      detail: 'allowance_spent',
      limit
    })

    const chat = getComparison('voted-id')
    const sent = await chat.ask('Encore une question')

    arena.refusal = undefined
    arena.comparisons = []
    expect(sent).toBe(false)
    expect(chat.promptError).toBeUndefined()
    expect(chat.pause).toEqual({ detail: 'allowance_spent', limit })
    expect(chat.canReveal).toBe(true)
  })

  it.each([
    ['by the server countdown, whatever the browser clock says', 600, 600],
    ['after two hours when the reset is unknown', null, 7200]
  ])('gives the send area back %s', async (_, resetsIn, liftsAfter) => {
    vi.useFakeTimers()
    arena.comparisons = [{ id: 'voted-id', turns: [] } as unknown as Comparison]
    arena.refusal = Object.assign(new ValidationError('allowance_spent'), {
      status: 429,
      detail: 'allowance_spent',
      // A clock time already past here, as from a server whose clock is ahead.
      limit: { ...limit, resets_at: '2000-01-01T00:00:00Z', resets_in: resetsIn }
    })

    const chat = getComparison('voted-id')
    await chat.ask('Encore une question')
    arena.refusal = undefined
    arena.comparisons = []

    vi.advanceTimersByTime(liftsAfter * 1000 - 1)
    expect(chat.pause).toBeDefined()
    vi.advanceTimersByTime(1)
    expect(chat.pause).toBeUndefined()
    vi.useRealTimers()
  })

  it('leaves a refusal with no limit to the input error', async () => {
    const comparison = {
      id: 'voted-id',
      turns: [{ id: 'turn-id', status: 'complete', choice: 'a_better', a: {}, b: {} }]
    } as unknown as Comparison
    arena.comparisons = [comparison]
    arena.refusal = Object.assign(new ValidationError('block_cooldown'), {
      status: 429,
      detail: 'block_cooldown'
    })

    const chat = getComparison('voted-id')
    await chat.ask('Encore une question')

    arena.refusal = undefined
    arena.comparisons = []
    expect(chat.pause).toBeUndefined()
    expect(chat.promptError).toBeTruthy()
    // The reveal stays open after this refusal too.
    expect(chat.canReveal).toBe(true)
  })
})
