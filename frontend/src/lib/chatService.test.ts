import { describe, expect, it, vi } from 'vitest'
import {
  getComparison,
  parseAPIComparison,
  type APIComparison,
  type Comparison
} from './chatService.svelte'
import { ValidationError } from './fastapi-client'
import { getLocale } from './i18n/runtime'

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

describe('askFirst', () => {
  const args = { prompt_value: 'Bonjour', tools: [] as string[] }

  function stubCohorts(value: string) {
    vi.stubGlobal('sessionStorage', { getItem: () => value })
  }

  it('sends the mode key, the language and no selection when nothing is picked', async () => {
    streamed.length = 0
    stubCohorts('pix')

    await getComparison(undefined).askFirst({ ...args, mode: 'legal', custom_models_selection: [] })

    expect(streamed[0].body).toMatchObject({
      mode: 'legal',
      custom_models_selection: null,
      locale: getLocale(),
      cohorts: 'pix'
    })
  })

  it('sends the picked models in any mode that lets the visitor pick', async () => {
    streamed.length = 0
    stubCohorts('')

    await getComparison(undefined).askFirst({
      ...args,
      mode: 'champion',
      custom_models_selection: ['a']
    })

    expect(streamed[0].body).toMatchObject({ mode: 'champion', custom_models_selection: ['a'] })
  })

  it('tells the visitor and keeps the key when the mode is no longer on offer', async () => {
    stubCohorts('')
    arena.refusal = Object.assign(new Error('Error 400'), {
      status: 400,
      detail: 'mode_unavailable'
    })

    const chat = getComparison(undefined)
    const sent = await chat.askFirst({ ...args, mode: 'gone', custom_models_selection: [] })

    arena.refusal = undefined
    expect(sent).toBe(false)
    expect(chat.promptErrorKey).toBe('mode_unavailable')
    expect(chat.promptError).toMatch(/mode/i)
  })
})
