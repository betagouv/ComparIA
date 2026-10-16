import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArenaLimits } from './generated/backend'
import { createLimits } from './limits.svelte'

const server = vi.hoisted(() => ({
  reads: [] as ((signal: AbortSignal) => Promise<unknown>)[],
  calls: 0
}))

vi.mock('$app/environment', () => ({ browser: true }))
vi.mock('$lib/fastapi-client', () => ({
  api: {
    request: (url: string, options: RequestInit) => {
      expect(url).toBe('/arena/limits')
      server.calls++
      const next = server.reads.shift()
      return next ? next(options.signal!) : Promise.resolve(open)
    }
  }
}))

const open: ArenaLimits = { total: null, expensive: null, signed_in_factor: 3, paused_llms: [] }
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
      signed_in_factor: 3,
      paused_llms: [{ id: 'gpt', until: wrongClock, reason: 'allowance' }]
    })

    expect(limits.expensive?.resets_at).toBe('2026-10-14T10:10:00.000Z')
    expect(limits.paused.get('gpt')?.until).toBe('2026-10-14T10:10:00.000Z')
    expect(limits.total).toBeUndefined()
    limits.destroy()
  })

  it('keeps the signed-in factor the server says, unknown before a read', async () => {
    const limits = createLimits()
    expect(limits.signedInFactor).toBeUndefined()

    reply({ ...open, signed_in_factor: 2.5 })
    await limits.refresh()
    expect(limits.signedInFactor).toBe(2.5)
  })

  it('says it has not read the limits yet until the first read lands', async () => {
    let land: (data: ArenaLimits) => void = () => {}
    server.reads.push(() => new Promise((resolve) => (land = resolve)))
    const limits = createLimits(null, { pending: true })

    expect(limits.read).toBe(false)
    const reading = limits.refresh()
    expect(limits.read).toBe(false)
    land(open)
    await reading

    expect(limits.read).toBe(true)
    expect(createLimits().read).toBe(true)
    limits.destroy()
  })

  it("counts the first wait from the page's load, so a slow hydration does not add to it", async () => {
    vi.resetModules()
    const { createLimits: onLoad } = await import('./limits.svelte')
    // The page took 1.5 s to hydrate.
    vi.advanceTimersByTime(1500)
    const limits = onLoad(null, { pending: true })

    vi.advanceTimersByTime(499)
    expect(limits.read).toBe(false)
    vi.advanceTimersByTime(1)
    expect(limits.read).toBe(true)
    limits.destroy()
    // A layout made later, on a navigation, waits the whole two seconds.
    const later = onLoad(null, { pending: true })
    vi.advanceTimersByTime(1999)
    expect(later.read).toBe(false)
    later.destroy()
  })

  it('stops waiting for a read that never lands', () => {
    const limits = createLimits(null, { pending: true })

    vi.advanceTimersByTime(2000)

    expect(limits.read).toBe(true)
    limits.destroy()
  })

  it('abandons a read that hangs, and shows the forms meanwhile', async () => {
    let aborted = false
    server.reads.push(
      (signal) =>
        new Promise((_, reject) =>
          signal.addEventListener('abort', () => {
            aborted = true
            reject(new DOMException('Aborted', 'AbortError'))
          })
        )
    )
    const limits = createLimits(null, { pending: true })
    const reading = limits.refresh()

    await vi.advanceTimersByTimeAsync(2000)
    expect(limits.read).toBe(true)
    expect(aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(8000)

    expect(aborted).toBe(true)
    expect(await reading).toBe(false)
    limits.destroy()
  })

  it('shows the forms at once when the read fails', async () => {
    reply(new Error('500'))
    const limits = createLimits(null, { pending: true })

    expect(await limits.refresh()).toBe(false)
    expect(limits.read).toBe(true)
    limits.destroy()
  })

  it("keeps the server's reset time while this clock agrees with it, so reads do not move it", () => {
    const at = '2026-10-14T10:09:59Z'
    // Two reads a moment apart: the countdown lost a second, the time did not.
    const first = createLimits({
      total: { scope: 'session', resets_at: at, resets_in: 600 },
      expensive: null,
      signed_in_factor: 3,
      paused_llms: []
    })
    vi.setSystemTime(new Date('2026-10-14T10:00:00.700Z'))
    const second = createLimits({
      total: { scope: 'session', resets_at: at, resets_in: 599 },
      expensive: null,
      signed_in_factor: 3,
      paused_llms: []
    })

    expect(first.total?.resets_at).toBe('2026-10-14T10:09:59.000Z')
    expect(second.total?.resets_at).toBe('2026-10-14T10:09:59.000Z')
    first.destroy()
    second.destroy()
  })

  it('reads again when a pause lifts and drops it once the server agrees', async () => {
    const limits = createLimits({
      total: { scope: 'network', resets_at: wrongClock, resets_in: 600 },
      expensive: null,
      signed_in_factor: 3,
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
      signed_in_factor: 3,
      paused_llms: []
    })
    reply({
      total: { scope: 'session', resets_at: wrongClock, resets_in: 60 },
      expensive: null,
      signed_in_factor: 3,
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
      signed_in_factor: 3,
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
      signed_in_factor: 3,
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
