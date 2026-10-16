import { browser } from '$app/environment'
import { api } from '$lib/fastapi-client'
import type {
  ArenaLimits,
  LimitRefusalBody,
  PausedLLM,
  SpentAllowance
} from '$lib/generated/backend'
import { createContext } from 'svelte'
import { SvelteMap } from 'svelte/reactivity'

/** One icon per state in the admin: paused for the person until a time, or
 * full for everyone until midnight. The arena says it in words, on a try. */
export const PAUSED_ICON = 'i-ri-pause-circle-line'
export const FULL_ICON = 'i-ri-calendar-close-line'

// A window of the allowances: the longest one with no known reset can last.
const FALLBACK_SECONDS = 2 * 60 * 60
// How long the form waits for the first read before showing anyway.
const FIRST_READ_MS = 2000
// A read that hangs is abandoned after this long.
const READ_TIMEOUT_MS = 10_000
let firstLoad = true
// Off by less than this, this browser's clock agrees with the server's.
const CLOCK_SKEW_MS = 60_000
// Never read again sooner than this, even when the server says it lifts now.
const MIN_WAIT_MS = 1000

/**
 * A spent allowance. `resets_at` is the server's, or, on a browser whose
 * clock is off from the server's, the countdown on this clock, so the time
 * shown agrees with the person's own clock.
 */
export interface Spent extends SpentAllowance {
  /** When to read the limits again, from the countdown or two hours. */
  liftsAt: number
}

export type Limits = ReturnType<typeof createLimits>

export const [getLimitsContext, setLimitsContext] = createContext<Limits>()

export async function queryLimits(): Promise<ArenaLimits | null> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), READ_TIMEOUT_MS)
  try {
    return await api.request<ArenaLimits>('/arena/limits', { signal: controller.signal })
  } catch (err) {
    // The arena works without it: a message is still charged, and refused, by
    // the server.
    console.error('Could not read the arena limits', err)
    return null
  } finally {
    clearTimeout(timer)
  }
}

function spent(allowance: SpentAllowance | null, now: number): Spent | undefined {
  if (!allowance) return undefined
  const resetsIn = allowance.resets_in
  if (resetsIn === null)
    return { ...allowance, resets_at: null, liftsAt: now + FALLBACK_SECONDS * 1000 }
  const counted = now + resetsIn * 1000
  // The server's time is fixed for the window, where the countdown loses a
  // second here and there between reads: keep it while this clock agrees
  // with it, and trust the countdown on a clock that is off.
  const server = allowance.resets_at ? Date.parse(allowance.resets_at) : NaN
  const at = Math.abs(server - counted) < CLOCK_SKEW_MS ? server : counted
  return { ...allowance, resets_at: new Date(at).toISOString(), liftsAt: at }
}

/**
 * What the arena may do for this person right now: the whole allowance
 * (`total`), the expensive one, and the models paused for them. Read on page
 * load, after each turn and refusal, and again when a pause lifts.
 */
export function createLimits(
  initial: ArenaLimits | null = null,
  { pending = false }: { pending?: boolean } = {}
) {
  // `pending` while a page rendered on the server waits for its first read:
  // the forms stay hidden meanwhile, or a spent allowance would show the
  // text box for a moment before the pause took its place.
  let read = $state(!pending)
  let waiting: ReturnType<typeof setTimeout> | undefined
  if (pending && browser) {
    // On the page's first load the wait counts from when it started loading,
    // so a slow hydration does not add to it.
    const since = firstLoad ? performance.now() : 0
    firstLoad = false
    waiting = setTimeout(() => (read = true), Math.max(0, FIRST_READ_MS - since))
  }
  let total = $state<Spent>()
  let expensive = $state<Spent>()
  // Unknown until the first read.
  let signedInFactor = $state<number>()
  const paused = new SvelteMap<string, PausedLLM>()
  let timer: ReturnType<typeof setTimeout> | undefined
  // Only the latest read counts: an older one may land after a refusal.
  let reads = 0

  function apply(data: ArenaLimits) {
    const now = Date.now()
    total = spent(data.total, now)
    expensive = spent(data.expensive, now)
    signedInFactor = data.signed_in_factor
    paused.clear()
    for (const llm of data.paused_llms) {
      paused.set(llm.id, {
        ...llm,
        until: llm.reason === 'allowance' ? (expensive?.resets_at ?? null) : llm.until
      })
    }
    arm()
  }

  function arm() {
    clearTimeout(timer)
    if (!browser) return
    const next = Math.min(total?.liftsAt ?? Infinity, expensive?.liftsAt ?? Infinity)
    if (next === Infinity) return
    timer = setTimeout(lift, Math.max(next - Date.now(), MIN_WAIT_MS))
  }

  async function lift() {
    if (!(await refresh())) {
      // The server cannot say: let the person try, a send is refused anyway.
      const now = Date.now()
      if (total && total.liftsAt <= now) total = undefined
      if (expensive && expensive.liftsAt <= now) {
        expensive = undefined
        for (const [id, llm] of paused) if (llm.reason === 'allowance') paused.delete(id)
      }
      arm()
    }
  }

  // The latest read, so a caller can wait on the one a refusal started
  // rather than read again.
  let latest: Promise<boolean> = Promise.resolve(false)

  /** Reads the limits again; false when the server could not tell. */
  function refresh(): Promise<boolean> {
    latest = load()
    return latest
  }

  async function load(): Promise<boolean> {
    const current = ++reads
    const data = await queryLimits()
    read = true
    clearTimeout(waiting)
    if (current !== reads) return true
    if (data) apply(data)
    return !!data
  }

  if (initial) apply(initial)

  return {
    /** Set while the whole allowance is spent: no message goes through. */
    get total() {
      return total
    },
    /** Set while the expensive allowance is spent. Shown in the picker only. */
    get expensive() {
      return expensive
    },
    /** How many times the personal allowances signing in gives. */
    get signedInFactor() {
      return signedInFactor
    },
    /** The models a new comparison may not use yet, by id. */
    get paused(): ReadonlyMap<string, PausedLLM> {
      return paused
    },
    /** False until the first read lands on a page rendered on the server. */
    get read() {
      return read
    },
    refresh,
    /** Settles with the latest read, as `refresh` does. */
    get reading() {
      return latest
    },
    /** A message was refused on a limit: show it at once, then read the rest. */
    refused(refusal: LimitRefusalBody) {
      if (refusal.detail === 'allowance_spent') {
        reads++
        const { scope, resets_at, resets_in } = refusal.limit
        total = spent({ scope: scope ?? 'session', resets_at, resets_in }, Date.now())
        arm()
      }
      void refresh()
    },
    destroy() {
      clearTimeout(timer)
      clearTimeout(waiting)
    }
  }
}
