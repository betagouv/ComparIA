<script lang="ts" module>
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { FULL_ICON } from '$lib/limits.svelte'
  import { resetTime, spoken, type ResetTime } from './resetTime'

  /** Models taken out of the person's pick. */
  export interface TrimmedPause {
    kind: 'trimmed'
    /** The models taken out because their day is full, for everyone. */
    full: string[]
    /** The models taken out because the expensive allowance is spent. */
    paused: string[]
    /** When the paused ones come back, null when unknown. */
    until: string | null
    /** Taking them out emptied the selection, so the mode went back to random. */
    toRandom: boolean
    /** The network spent the allowance, not just this person. */
    network: boolean
  }

  /** What the home form changed, or cannot do, for models paused for the person. */
  export type PickPause =
    | TrimmedPause
    | {
        kind: 'mode'
        until: string | null
        /** Its models are full for the day, for everyone, not paused for this person. */
        full: boolean
      }

  const TRIMMED = {
    one: {
      kept: 'arene.limits.picker.trimmedOne',
      toRandom: 'arene.limits.picker.trimmedOneToRandom'
    },
    two: {
      kept: 'arene.limits.picker.trimmedTwo',
      toRandom: 'arene.limits.picker.trimmedTwoToRandom'
    }
  } as const
  const TRIMMED_NETWORK = {
    one: {
      kept: 'arene.limits.picker.trimmedOneNetwork',
      toRandom: 'arene.limits.picker.trimmedOneToRandomNetwork'
    },
    two: {
      kept: 'arene.limits.picker.trimmedTwoNetwork',
      toRandom: 'arene.limits.picker.trimmedTwoToRandomNetwork'
    }
  } as const

  const TRIMMED_FULL = {
    one: {
      kept: 'arene.limits.picker.trimmedFullOne',
      toRandom: 'arene.limits.picker.trimmedFullOneToRandom'
    },
    two: {
      kept: 'arene.limits.picker.trimmedFullTwo',
      toRandom: 'arene.limits.picker.trimmedFullTwoToRandom'
    }
  } as const
  const TRIMMED_MIXED = {
    kept: 'arene.limits.picker.trimmedMixed',
    toRandom: 'arene.limits.picker.trimmedMixedToRandom'
  } as const
  const TRIMMED_MIXED_NETWORK = {
    kept: 'arene.limits.picker.trimmedMixedNetwork',
    toRandom: 'arene.limits.picker.trimmedMixedToRandomNetwork'
  } as const

  function list(names: string[]) {
    return new Intl.ListFormat(getLocale(), { type: 'conjunction' }).format(names)
  }

  function copy(pause: PickPause): { reset: ResetTime; text: string; why: string; icon?: string } {
    const reset = resetTime(pause.until)
    if (pause.kind === 'mode' && pause.full) {
      return {
        reset,
        icon: FULL_ICON,
        text: m['arene.limits.mode.hintFull'](),
        why: m['arene.limits.mode.whyFull']()
      }
    }
    if (pause.kind === 'mode') {
      return {
        reset,
        text: m['arene.limits.mode.hint']({ until: reset.until }),
        why: m['arene.limits.mode.why']()
      }
    }
    // Each model is told by its own reason, in one sentence: a full one is
    // back at midnight for everyone, a paused one when this person's
    // allowance lifts. The comparison going random is said once, at the end.
    const { full, paused, toRandom } = pause
    const end = toRandom ? 'toRandom' : 'kept'
    const fullWhy = m['arene.limits.picker.fullWhy']()
    const pausedWhy =
      m[pause.network ? 'arene.limits.picker.whyNetwork' : 'arene.limits.picker.why']()
    if (full.length && paused.length) {
      const key = (pause.network ? TRIMMED_MIXED_NETWORK : TRIMMED_MIXED)[end]
      return {
        reset,
        text: m[key]({ full: list(full), paused: list(paused), until: reset.until }),
        why: `${fullWhy} ${pausedWhy}`
      }
    }
    if (full.length) {
      const key = TRIMMED_FULL[full.length > 1 ? 'two' : 'one'][end]
      return { reset, icon: FULL_ICON, text: m[key]({ models: list(full) }), why: fullWhy }
    }
    // "pour votre réseau" when the network spent it, as the picker says.
    const key = (pause.network ? TRIMMED_NETWORK : TRIMMED)[paused.length > 1 ? 'two' : 'one'][end]
    return { reset, text: m[key]({ models: list(paused), until: reset.until }), why: pausedWhy }
  }

  /** The notice as a screen reader hears it, for the form's live region. */
  export function pickPauseSaid(pause: PickPause): string {
    const { reset, text } = copy(pause)
    return spoken(text, reset)
  }
</script>

<script lang="ts">
  import LimitHint from './LimitHint.svelte'

  let {
    pause,
    focusOnShow = false
  }: {
    pause: PickPause
    /** It answers a refused send: focus it, or nothing tells why nothing started. */
    focusOnShow?: boolean
  } = $props()

  const { reset, text, why, icon } = $derived(copy(pause))
</script>

<LimitHint id="pick-paused-notice" {text} {reset} {why} {icon} {focusOnShow} />
