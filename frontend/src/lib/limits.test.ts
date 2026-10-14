import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArenaLimits } from './generated/backend'
import { createLimits } from './limits.svelte'

const server = vi.hoisted(() => ({
  reads: [] as (() => Promise<unknown>)[],
  calls: 0
}))

vi.mock('$app/environment', () => ({ browser: true }))
vi.mock('$lib/fastapi-client', () => ({
  api: {
    request: (url: string) => {
      expect(url).toBe('/arena/limits')
      server.calls++
      const next = server.reads.shift()
      return next ? next() : Promise.resolve(open)
    }
  }
}))

const open: ArenaLimits = { total: null, expensive: null, paused_llms: [] }
// A clock time long past, as from a server whose clock is far ahead.
const wrongClock = '2000-01-01T00:00:00Z'

function reply(data: ArenaLimits | Error) {
  server.reads.push(() => (data instanceof Error ? Promise.reject(data) : Promise.resolve(data)))
}

describe('createLimits', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-14T10:00:00Z'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.reads = []
    server.calls = 0
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('tells the reset from the server countdown, on this browser clock', () => {
    const limits = createLimits({
      total: null,
      expensive: { scope: 'session', resets_at: wrongClock, resets_in: 600 },
      paused_llms: [{ id: 'gpt', until: wrongClock, reason: 'allowance' }]
    })

    expect(limits.expensive?.resets_at).toBe('2026-10-14T10:10:00.000Z')
    expect(limits.paused.get('gpt')?.until).toBe('2026-10-14T10:10:00.000Z')
    expect(limits.total).toBeUndefined()
    limits.destroy()
  })

  it('reads again when a pause lifts and drops it once the server agrees', async () => {
    const limits = createLimits({
      total: { scope: 'network', resets_at: wrongClock, resets_in: 600 },
      expensive: null,
      paused_llms: []
    })

    await vi.advanceTimersByTimeAsync(599_000)
    expect(server.calls).toBe(0)
    await vi.advanceTimersByTimeAsync(1000)
    expect(server.calls).toBe(1)
    expect(limits.total).toBeUndefined()
  })

  it('keeps a pause the server still holds, and waits two hours when it cannot tell when', async () => {
    const limits = createLimits({
      total: { scope: 'session', resets_at: null, resets_in: null },
      expensive: null,
      paused_llms: []
    })
    reply({
      total: { scope: 'session', resets_at: wrongClock, resets_in: 60 },
      expensive: null,
      paused_llms: []
    })

    await vi.advanceTimersByTimeAsync(7_200_000)
    expect(server.calls).toBe(1)
    expect(limits.total?.resets_in).toBe(60)

    await vi.advanceTimersByTimeAsync(60_000)
    expect(server.calls).toBe(2)
    expect(limits.total).toBeUndefined()
  })

  it('lifts a pause when its time comes even if the server cannot be read', async () => {
    const limits = createLimits({
      total: { scope: 'session', resets_at: wrongClock, resets_in: 30 },
      expensive: { scope: 'session', resets_at: wrongClock, resets_in: 30 },
      paused_llms: [
        { id: 'gpt', until: wrongClock, reason: 'allowance' },
        { id: 'full', until: '2026-10-15T00:00:00Z', reason: 'full' }
      ]
    })
    reply(new Error('offline'))

    await vi.advanceTimersByTimeAsync(30_000)
    expect(limits.total).toBeUndefined()
    expect(limits.expensive).toBeUndefined()
    expect([...limits.paused.keys()]).toEqual(['full'])
  })

  it('shows a refused message at once, and an older read landing after does not undo it', async () => {
    const limits = createLimits()
    let landOld: (data: ArenaLimits) => void = () => {}
    server.reads.push(() => new Promise((resolve) => (landOld = resolve)))
    reply({
      total: { scope: 'session', resets_at: wrongClock, resets_in: 900 },
      expensive: null,
      paused_llms: []
    })

    const older = limits.refresh()
    limits.refused({
      detail: 'allowance_spent',
      limit: { scope: 'session', resets_at: wrongClock, resets_in: 900, llm_ids: [] }
    })
    expect(limits.total?.resets_at).toBe('2026-10-14T10:15:00.000Z')

    landOld(open)
    await older
    await vi.advanceTimersByTimeAsync(0)
    expect(limits.total).toBeDefined()
    limits.destroy()
  })
})
