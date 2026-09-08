import { describe, expect, it, vi } from 'vitest'
import { FastAPIClient, SSE_INACTIVITY_TIMEOUT_MS, StreamTimeoutError } from './fastapi-client'

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
