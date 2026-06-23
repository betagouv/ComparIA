/**
 * Altcha CAPTCHA state management.
 *
 * Fetches a PoW challenge from the backend, solves it using Web Crypto API,
 * and provides the token for inclusion in API requests.
 * Auto-solves on page load so users experience zero added latency.
 */
import { browser } from '$app/environment'
import { api } from '$lib/fastapi-client'

interface AltchaChallenge {
  algorithm: string
  challenge: string
  maxNumber: number
  salt: string
  signature: string
}

// Server expiry is 600s. Refresh comfortably before that.
const TOKEN_STALE_AFTER_MS = 8 * 60 * 1000

export class CaptchaError extends Error {
  constructor(message: string, public cause?: unknown) {
    super(message)
    this.name = 'CaptchaError'
  }
}

let altchaToken = $state<string | null>(null)
let tokenCreatedAt = 0
let inflight: Promise<void> | null = null

function isStale(): boolean {
  return !altchaToken || Date.now() - tokenCreatedAt > TOKEN_STALE_AFTER_MS
}

export function getAltchaToken(): string | null {
  return altchaToken
}

/**
 * Return a fresh token and start solving the next one.
 * Throws CaptchaError if no token can be produced — callers should surface
 * this to the user rather than POST a null token to the backend.
 */
export async function consumeAltchaToken(): Promise<string> {
  if (isStale()) {
    await fetchAndSolve()
  }
  const token = altchaToken
  if (!token) {
    throw new CaptchaError('Captcha token unavailable')
  }
  altchaToken = null
  tokenCreatedAt = 0
  // Start the next solve so the following request is instant.
  void fetchAndSolveSilently()
  return token
}

async function solveChallenge(
  challenge: string,
  salt: string,
  algorithm: string,
  max: number
): Promise<number | null> {
  const encoder = new TextEncoder()
  for (let n = 0; n <= max; n++) {
    const data = encoder.encode(salt + n)
    const hashBuffer = await crypto.subtle.digest(algorithm, data)
    const hex = [...new Uint8Array(hashBuffer)].map((b) => b.toString(16).padStart(2, '0')).join('')
    if (hex === challenge) return n
  }
  return null
}

/**
 * Fetch a challenge and solve it. Concurrent calls share the in-flight promise.
 * Rejects on network or solve failure — callers that want fire-and-forget
 * behaviour should use fetchAndSolveSilently().
 */
export function fetchAndSolve(): Promise<void> {
  if (!browser) return Promise.resolve()
  if (inflight) return inflight
  if (altchaToken && !isStale()) return Promise.resolve()

  inflight = (async () => {
    try {
      let challenge: AltchaChallenge
      try {
        challenge = await api.request<AltchaChallenge>('/arena/challenge')
      } catch (err) {
        throw new CaptchaError('Failed to fetch captcha challenge', err)
      }
      const number = await solveChallenge(
        challenge.challenge,
        challenge.salt,
        challenge.algorithm,
        challenge.maxNumber
      )
      if (number === null) {
        throw new CaptchaError('Failed to solve challenge within maxNumber range')
      }
      const payload = {
        algorithm: challenge.algorithm,
        challenge: challenge.challenge,
        number,
        salt: challenge.salt,
        signature: challenge.signature
      }
      altchaToken = btoa(JSON.stringify(payload))
      tokenCreatedAt = Date.now()
      console.debug('[ALTCHA] Challenge solved')
    } finally {
      inflight = null
    }
  })()

  return inflight
}

/**
 * Background variant for page-load and visibility refresh: never throws.
 */
export function fetchAndSolveSilently(): Promise<void> {
  return fetchAndSolve().catch((error) => {
    console.error('[ALTCHA] Background solve failed:', error)
  })
}

if (browser) {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isStale()) {
      void fetchAndSolveSilently()
    }
  })
}
