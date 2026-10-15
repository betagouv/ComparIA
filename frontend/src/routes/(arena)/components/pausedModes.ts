import type { Mode } from '$lib/chatService.svelte'
import {
  BIG_MODELS_BUCKET_LOWER_LIMIT,
  SMALL_MODELS_BUCKET_UPPER_LIMIT
} from '$lib/generated/constants'
import type { PausedModel } from '$lib/limits.svelte'

type Sized = { id?: string; params: number }

/**
 * The modes the server could not draw a pair for, with paused models left
 * out, and when they come back: the earliest return among the paused models
 * they draw from, null when unknown. Mirrors `LLMsData.pick_two`.
 */
export function pausedModes(
  models: Sized[],
  paused: ReadonlyMap<string, PausedModel>
): Map<Mode, string | null> {
  const small = models.filter((llm) => llm.params <= SMALL_MODELS_BUCKET_UPPER_LIMIT)
  const big = models.filter((llm) => llm.params >= BIG_MODELS_BUCKET_LOWER_LIMIT)
  // Each mode, by the pools it draws its two sides from.
  const sides: [Mode, Sized[][]][] = [
    ['random', [models, models]],
    ['small-models', [small, small]],
    ['big-vs-small', [big, small]]
  ]

  const out = new Map<Mode, string | null>()
  for (const [mode, pools] of sides) {
    // Two sides from one pool need two different models.
    const needed = pools[0] === pools[1] ? 2 : 1
    const draws = (from: Sized[][]) => from.every((pool) => pool.length >= needed)
    const open = pools.map((pool) => pool.filter((llm) => !paused.has(llm.id!)))
    // Not drawable even with nothing paused: not for the limits to tell.
    if (draws(open) || !draws(pools)) continue
    const back = pools
      .flat()
      .map((llm) => paused.get(llm.id!))
      .filter((llm): llm is PausedModel => !!llm)
    const known = back.map((llm) => llm.until).filter((until): until is string => !!until)
    out.set(mode, known.sort()[0] ?? null)
  }
  return out
}

/**
 * The modes that the models full for the day leave with nothing on their
 * own, for everyone until midnight, whatever this person's allowance.
 */
export function fullModes(models: Sized[], paused: ReadonlyMap<string, PausedModel>): Set<Mode> {
  const full = new Map([...paused].filter(([, llm]) => llm.reason === 'full'))
  return new Set(pausedModes(models, full).keys())
}
