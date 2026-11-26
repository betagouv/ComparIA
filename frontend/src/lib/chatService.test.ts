import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
  refusal: undefined as Error | undefined,
  events: [] as unknown[]
}))

vi.mock('$app/navigation', () => ({ goto: vi.fn() }))
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

describe('askFirst', () => {
  const ids = ['gemma', 'mistral']

  // This file runs in Node, which may have no sessionStorage.
  beforeEach(() => {
    vi.stubGlobal('sessionStorage', { getItem: () => '' })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the chosen model ids in manual mode', async () => {
    streamed.length = 0

    await getComparison(undefined).askFirst({
      mode: 'custom',
      custom_models_selection: ids,
      prompt_value: 'Bonjour',
      web_search: false
    })

    expect(streamed).toHaveLength(1)
    expect(streamed[0].url).toBe('/arena/add_first_text')
    expect(streamed[0].body).toMatchObject({ mode: 'custom', custom_models_selection: ids })
  })

  it.each(['random', 'small-models', 'big-vs-small'] as const)(
    'sends no model ids in %s mode, even if some are saved',
    async (mode) => {
      streamed.length = 0

      await getComparison(undefined).askFirst({
        mode,
        custom_models_selection: ids,
        prompt_value: 'Bonjour',
        web_search: false
      })

      expect(streamed[0].body).toMatchObject({ mode, custom_models_selection: null })
    }
  )
})

describe('streamed chunks', () => {
  it('keeps the tool steps already shown when a chunk carries none', async () => {
    const comparison = {
      id: 'tools-id',
      turns: [{ id: 'turn-id', status: 'error', a: {}, b: {} }]
    } as unknown as Comparison
    const steps = [{ type: 'tool_call', tool_call_id: '1', name: 'search', arguments_json: '{}' }]
    arena.comparisons = [comparison]
    arena.events = [
      { type: 'chunk', pos: 'a', llm_msg: { content: '', agent_trace: steps } },
      { type: 'chunk', pos: 'a', llm_msg: { content: 'Voici' } },
      { type: 'chunk', pos: 'a', llm_msg: { content: 'Voici la réponse' } }
    ]

    await getComparison('tools-id').retry()

    arena.events = []
    arena.comparisons = []
    expect(comparison.turns[0].a.llm_msg?.content).toBe('Voici la réponse')
    expect(comparison.turns[0].a.llm_msg?.agent_trace).toEqual(steps)
  })
})
