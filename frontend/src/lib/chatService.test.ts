import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getComparison,
  parseAPIComparison,
  type APIComparison,
  type Comparison
} from './chatService.svelte'
import { ValidationError } from './fastapi-client'
import type { ArenaLimits } from './generated/backend'
import { createLimits, type Limits } from './limits.svelte'

const streamed = vi.hoisted(() => [] as { url: string; body: Record<string, unknown> }[])
const arena = vi.hoisted(() => ({
  comparisons: [] as unknown[],
  refusal: undefined as Error | undefined,
  limits: undefined as unknown,
  // What GET /arena/limits answers next, then an open arena.
  reads: [] as unknown[],
  events: [] as unknown[]
}))
const open = { total: null, expensive: null, paused_llms: [] }

vi.mock('$app/navigation', () => ({ goto: vi.fn() }))
vi.mock('$app/environment', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$app/environment')>()),
  browser: true
}))
vi.mock('$lib/limits.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/limits.svelte')>()),
  getLimitsContext: () => arena.limits
}))
vi.mock('$lib/captcha.svelte', () => ({
  CaptchaError: class extends Error {},
  consumeAltchaToken: async () => 'solved-token'
}))
vi.mock('$lib/fastapi-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/fastapi-client')>()),
  api: {
    async *stream(url: string, body: Record<string, unknown>) {
      if (arena.refusal) throw arena.refusal
      streamed.push({ url, body })
      yield* arena.events
    },
    async request(url: string) {
      if (url !== '/arena/limits') throw new Error(`unexpected ${url}`)
      return arena.reads.shift() ?? open
    }
  }
}))
vi.mock('svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('svelte')>()),
  createContext: () => [() => arena.comparisons, () => undefined]
}))

beforeEach(() => {
  arena.reads = []
  arena.limits = createLimits()
  // askFirst reads the cohorts, and Node has no sessionStorage before 25.
  vi.stubGlobal('sessionStorage', { getItem: () => '' })
})

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
    arena.reads = [{ ...open, total: limit }]

    const chat = getComparison('voted-id')
    const sent = await chat.ask('Encore une question')

    arena.refusal = undefined
    arena.comparisons = []
    expect(sent).toBe(false)
    expect(chat.promptError).toBeUndefined()
    expect(chat.pause).toMatchObject({
      detail: 'allowance_spent',
      limit: { scope: 'network', resets_in: 4210 }
    })
    expect(chat.canReveal).toBe(true)
    ;(arena.limits as Limits).destroy()
  })

  it.each([
    ['by the server countdown, whatever the browser clock says', 600, 600],
    ['after two hours when the reset is unknown', null, 7200]
  ])('gives the send area back %s', async (_, resetsIn, liftsAfter) => {
    vi.useFakeTimers()
    arena.comparisons = [{ id: 'voted-id', turns: [] } as unknown as Comparison]
    // A clock time already past here, as from a server whose clock is ahead.
    const spent = { ...limit, resets_at: '2000-01-01T00:00:00Z', resets_in: resetsIn }
    arena.refusal = Object.assign(new ValidationError('allowance_spent'), {
      status: 429,
      detail: 'allowance_spent',
      limit: spent
    })
    arena.reads = [{ ...open, total: spent }]

    const chat = getComparison('voted-id')
    await chat.ask('Encore une question')
    expect(chat.pauseFromSend).toBe(true)
    arena.refusal = undefined
    arena.comparisons = []

    await vi.advanceTimersByTimeAsync(liftsAfter * 1000 - 1)
    expect(chat.pause).toBeDefined()
    await vi.advanceTimersByTimeAsync(1)
    expect(chat.pause).toBeUndefined()
    ;(arena.limits as Limits).destroy()
    vi.useRealTimers()
  })

  it('shows a pause already spent before anyone sends, without taking focus', () => {
    arena.limits = createLimits({
      ...open,
      total: { scope: 'session', resets_at: null, resets_in: 600 }
    } as ArenaLimits)

    const home = getComparison(undefined)

    expect(home.pause?.limit.scope).toBe('session')
    expect(home.pauseFromSend).toBe(false)
    ;(arena.limits as Limits).destroy()
  })

  it('reads the limits again once a turn is through', async () => {
    arena.comparisons = [
      {
        id: 'voted-id',
        turns: [{ id: 'turn-id', status: 'complete', choice: 'a_better', a: {}, b: {} }]
      } as unknown as Comparison
    ]
    arena.reads = [{ ...open, total: { scope: 'network', resets_at: null, resets_in: 600 } }]
    const chat = getComparison('voted-id')
    arena.events = [{ type: 'complete' }]
    await chat.ask('Encore une question')
    arena.events = []
    arena.comparisons = []

    await vi.waitFor(() => expect(chat.pause?.limit.scope).toBe('network'))
    ;(arena.limits as Limits).destroy()
  })

  it('keeps the reveal shut on a failed comparison', () => {
    arena.comparisons = [
      {
        id: 'failed-id',
        error: 'provider_error',
        turns: [{ id: 'turn-id', status: 'complete', choice: 'a_better', a: {}, b: {} }]
      } as unknown as Comparison
    ]

    const chat = getComparison('failed-id')

    expect(chat.canReveal).toBe(false)
    arena.comparisons = []
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
  it('does not pause anyone over a pick of models paused for them', async () => {
    arena.refusal = Object.assign(new ValidationError('expensive_allowance_spent'), {
      status: 429,
      detail: 'expensive_allowance_spent',
      limit: { ...limit, llm_ids: ['expensive-id'] }
    })

    const chat = getComparison(undefined)
    const sent = await chat.askFirst({
      prompt_value: 'Bonjour',
      mode: 'custom',
      custom_models_selection: ['expensive-id'],
      web_search: false
    })

    arena.refusal = undefined
    expect(sent).toBe(false)
    expect(chat.pause).toBeUndefined()
    expect(chat.promptError).toBeUndefined()
    expect(chat.pickRefusal?.limit.llm_ids).toEqual(['expensive-id'])

    // Sending again starts afresh.
    await chat.askFirst({
      prompt_value: 'Bonjour',
      mode: 'random',
      custom_models_selection: [],
      web_search: false
    })
    expect(chat.pickRefusal).toBeUndefined()
  })
})
