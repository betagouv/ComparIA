import { m } from '$lib/i18n/messages'

// The keys the arena backend sends as `detail`, see backend/arena/router.py,
// backend/arena/models.py and backend/arena/checks.py.
const ARENA_ERRORS = {
  rate_limited: () => m['arene.apiErrors.rate_limited'](),
  block_cooldown: () => m['arene.apiErrors.block_cooldown'](),
  comparison_streaming: () => m['arene.apiErrors.comparison_streaming'](),
  max_turns_reached: () => m['arene.apiErrors.max_turns_reached'](),
  retry_unavailable: () => m['arene.apiErrors.retry_unavailable'](),
  captcha_failed: () => m['arene.apiErrors.captcha_failed'](),
  captcha_unavailable: () => m['arene.apiErrors.captcha_unavailable'](),
  spam_detected: () => m['arene.apiErrors.spam_detected']()
} as const

const PROMPT_CHECK_MESSAGES = {
  generic: () => m['arene.apiErrors.prompt_check.generic'](),
  self_harm: () => m['arene.apiErrors.prompt_check.self_harm'](),
  pii: () => m['arene.apiErrors.prompt_check.pii']()
} as const

export type ArenaErrorKey = keyof typeof ARENA_ERRORS
export type PromptCheckMessageKey = keyof typeof PROMPT_CHECK_MESSAGES

export function isArenaErrorKey(detail: unknown): detail is ArenaErrorKey {
  return typeof detail === 'string' && detail in ARENA_ERRORS
}

/** The sentence for a backend `detail`, or the detail itself when unknown. */
export function arenaErrorMessage(detail: string): string {
  if (isArenaErrorKey(detail)) return ARENA_ERRORS[detail]()
  // Pydantic prefixes the message of a failed field validator.
  const stripped = detail.replace(/^Value error, /, '')
  return isArenaErrorKey(stripped) ? ARENA_ERRORS[stripped]() : detail
}

/**
 * The sentence for a prompt check verdict. Results stored before the keys
 * existed carry the sentence itself and come back as they are.
 */
export function promptCheckMessage(key: string): string {
  return key in PROMPT_CHECK_MESSAGES ? PROMPT_CHECK_MESSAGES[key as PromptCheckMessageKey]() : key
}
