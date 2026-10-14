<script lang="ts" module>
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { resetTime, spoken } from './resetTime'

  /** What the home form changed, or cannot do, for models paused for the person. */
  export type PickPause =
    | {
        kind: 'trimmed'
        /** The names of the models taken out of the selection. */
        names: string[]
        /** When the first of them comes back, null when unknown. */
        until: string | null
        /** They are all full for today rather than paused for this person. */
        full: boolean
        /** Taking them out emptied the selection, so the mode went back to random. */
        toRandom: boolean
        /** The network spent the allowance, not just this person. */
        network: boolean
      }
    | { kind: 'mode'; until: string | null }

  function copy(pause: PickPause) {
    const reset = resetTime(pause.until)
    if (pause.kind === 'mode') {
      return {
        reset,
        text: m['arene.limits.mode.hint']({ until: reset.until }),
        why: m['arene.limits.mode.why']()
      }
    }
    const models = new Intl.ListFormat(getLocale(), { type: 'conjunction' }).format(pause.names)
    const why = m[pause.network ? 'arene.limits.picked.whyNetwork' : 'arene.limits.picked.why']()
    if (pause.full) {
      // Full for everyone until midnight, not this person's allowance.
      return {
        reset,
        why: m['arene.limits.picker.fullWhy'](),
        text: m['arene.limits.picker.trimmedFull']({ models })
      }
    }
    const two = pause.names.length > 1
    const key = pause.toRandom
      ? two
        ? 'arene.limits.picker.trimmedTwoToRandom'
        : 'arene.limits.picker.trimmedOneToRandom'
      : two
        ? 'arene.limits.picker.trimmedTwo'
        : 'arene.limits.picker.trimmedOne'
    return { reset, why, text: m[key]({ models, until: reset.until }) }
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

  const { reset, text, why } = $derived(copy(pause))
</script>

<LimitHint id="pick-paused-notice" {text} {reset} {why} {focusOnShow} />
