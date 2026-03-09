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

let altchaToken = $state<string | null>(null)
let solving = $state(false)

export function getAltchaToken(): string | null {
  return altchaToken
}

/**
 * Consume the current token and start solving a new one.
 */
export function consumeAltchaToken(): string | null {
  const token = altchaToken
  altchaToken = null
  fetchAndSolve()
  return token
}

/**
 * Solve a SHA-256 proof-of-work challenge using Web Crypto API.
 */
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
 * Fetch a challenge from the backend and solve it.
 */
export async function fetchAndSolve(): Promise<void> {
  if (!browser || solving || altchaToken) return

  solving = true
  try {
    const challenge = await api.request<AltchaChallenge>('/arena/challenge')

    const number = await solveChallenge(
      challenge.challenge,
      challenge.salt,
      challenge.algorithm,
      challenge.maxNumber
    )

    if (number !== null) {
      const payload = {
        algorithm: challenge.algorithm,
        challenge: challenge.challenge,
        number,
        salt: challenge.salt,
        signature: challenge.signature
      }
      altchaToken = btoa(JSON.stringify(payload))
      console.debug('[ALTCHA] Challenge solved')
    } else {
      console.error('[ALTCHA] Failed to solve challenge')
    }
  } catch (error) {
    console.error('[ALTCHA] Error:', error)
  } finally {
    solving = false
  }
}
