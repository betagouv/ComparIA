import type { LLMHealth } from '$lib/generated/admin'

/** The browser adds `request_failed` when the call itself fails. */
export type LLMHealthResult = Omit<LLMHealth, 'error'> & {
  error?: LLMHealth['error'] | 'request_failed'
}
