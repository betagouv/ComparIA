import { describe, expect, it, vi } from 'vitest'
import {
  FastAPIClient,
  SSE_INACTIVITY_TIMEOUT_MS,
  StreamTimeoutError,
  type ApiError
} from './fastapi-client'

describe('FastAPIClient.stream', () => {
  it('fails a silent SSE connection after the inactivity timeout', async () => {
    vi.useFakeTimers()
    const read = vi.fn(() => new Promise<ReadableStreamReadResult<Uint8Array>>(() => {}))
    const cancel = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        body: { getReader: () => ({ read, cancel }) }
      })
    )

    const next = new FastAPIClient('https://example.test').stream('/arena', {}).next()
    const rejection = expect(next).rejects.toBeInstanceOf(StreamTimeoutError)
    await vi.advanceTimersByTimeAsync(SSE_INACTIVITY_TIMEOUT_MS)

    await rejection
    expect(cancel).toHaveBeenCalled()
    vi.useRealTimers()
  })
})

describe('FastAPIClient.parseErrorResponse', () => {
  const client = new FastAPIClient('https://example.test')

  it('keeps the limit a refusal carries beside its key', async () => {
    const limit = {
      scope: 'network',
      resets_at: '2026-10-13T13:40:00Z',
      resets_in: 4210,
      llm_ids: []
    }
    const response = new Response(JSON.stringify({ detail: 'allowance_spent', limit }), {
      status: 429
    })

    const error: ApiError = await client.parseErrorResponse(response, '/arena/add_text', 'POST')

    expect(error.status).toBe(429)
    expect(error.detail).toBe('allowance_spent')
    expect(error.limit).toEqual(limit)
  })

  it('leaves limit out of any other error', async () => {
    const response = new Response(JSON.stringify({ detail: 'block_cooldown' }), { status: 429 })

    const error: ApiError = await client.parseErrorResponse(response, '/arena/add_text', 'POST')

    expect(error.detail).toBe('block_cooldown')
    expect(error.limit).toBeUndefined()
  })
})
