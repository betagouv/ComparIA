import type { Mode } from '$lib/chatService.svelte'
import {
  BIG_MODELS_BUCKET_LOWER_LIMIT,
  SMALL_MODELS_BUCKET_UPPER_LIMIT
} from '$lib/generated/constants'
import type { PausedLLM } from '$lib/generated/backend'

type Sized = { id?: string; params: number }

export interface ModePause {
  /** The earliest return among the paused models it draws from, null when unknown. */
  until: string | null
  /** The models full for the day leave it with nothing on their own, for
   * everyone until midnight, whatever this person's allowance. */
  full: boolean
}

/**
 * The modes the server could not draw a pair for, with paused models left
 * out, and when they come back. Mirrors `LLMsData.pick_two`.
 */
export function pausedModes(
  models: Sized[],
  paused: ReadonlyMap<string, PausedLLM>
): Map<Mode, ModePause> {
  const small = models.filter((llm) => llm.params <= SMALL_MODELS_BUCKET_UPPER_LIMIT)
  const big = models.filter((llm) => llm.params >= BIG_MODELS_BUCKET_LOWER_LIMIT)
  // Each mode, by the pools it draws its two sides from.
  const sides: [Mode, Sized[][]][] = [
    ['random', [models, models]],
    ['small-models', [small, small]],
    ['big-vs-small', [big, small]]
  ]
  const isPaused = (llm: Sized) => paused.has(llm.id!)
  const isFull = (llm: Sized) => paused.get(llm.id!)?.reason === 'full'

  const out = new Map<Mode, ModePause>()
  for (const [mode, pools] of sides) {
    // Two sides from one pool need two different models.
    const needed = pools[0] === pools[1] ? 2 : 1
    const draws = (leftOut: (llm: Sized) => boolean = () => false) =>
      pools.every((pool) => pool.filter((llm) => !leftOut(llm)).length >= needed)
    // Not drawable even with nothing paused: not for the limits to tell.
    if (draws(isPaused) || !draws()) continue
    const known = pools
      .flat()
      .map((llm) => paused.get(llm.id!)?.until)
      .filter((until): until is string => !!until)
    out.set(mode, { until: known.sort()[0] ?? null, full: !draws(isFull) })
  }
  return out
}
