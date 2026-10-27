import { describe, expect, it, vi } from 'vitest'
import { FastAPIClient, SSE_INACTIVITY_TIMEOUT_MS, StreamTimeoutError } from './fastapi-client'

vi.mock('$app/environment', () => ({ browser: false, dev: false }))
vi.mock('$env/dynamic/public', () => ({
  env: { PUBLIC_API_LOCAL_URL: 'http://backend:8001', PUBLIC_API_URL: 'https://comparia.test' }
}))

describe('FastAPIClient.getPublicUrl', () => {
  it('never renders the in-cluster backend address during SSR', () => {
    const client = new FastAPIClient('http://backend:8001/api')

    expect(client.getUrl('/auth/config/logo')).toBe('http://backend:8001/api/auth/config/logo')
    expect(client.getPublicUrl('/auth/config/logo', { v: '3' })).toBe('/api/auth/config/logo?v=3')
    expect(client.getPublicUrl('/auth/config/oidc/logo')).toBe('/api/auth/config/oidc/logo')
  })
})

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
