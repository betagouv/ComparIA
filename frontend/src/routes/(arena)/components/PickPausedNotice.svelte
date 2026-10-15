<script lang="ts" module>
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { resetTime, spoken } from './resetTime'

  /** What the home form changed, or cannot do, for models paused for the person. */
  export type PickPause =
    | {
        kind: 'trimmed'
        /** The models taken out because their day is full, for everyone. */
        full: string[]
        /** The models taken out because the expensive allowance is spent. */
        paused: string[]
        /** When the first paused one comes back, null when unknown. */
        until: string | null
        /** Taking them out emptied the selection, so the mode went back to random. */
        toRandom: boolean
        /** The network spent the allowance, not just this person. */
        network: boolean
      }
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

  function list(names: string[]) {
    return new Intl.ListFormat(getLocale(), { type: 'conjunction' }).format(names)
  }

  function copy(pause: PickPause) {
    const reset = resetTime(pause.until)
    if (pause.kind === 'mode' && pause.full) {
      return {
        reset,
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
    // Each model is told by its own reason: a full one is back at midnight
    // for everyone, a paused one when this person's allowance lifts. The
    // comparison going random is said once, at the end.
    const { full, paused, toRandom } = pause
    const text: string[] = []
    const why: string[] = []
    if (full.length) {
      const key =
        toRandom && !paused.length
          ? 'arene.limits.picker.trimmedFullToRandom'
          : 'arene.limits.picker.trimmedFull'
      text.push(m[key]({ models: list(full) }))
      why.push(m['arene.limits.picker.fullWhy']())
    }
    if (paused.length) {
      // "pour votre réseau" when the network spent it, as the picker says.
      const keys = pause.network ? TRIMMED_NETWORK : TRIMMED
      const key = keys[paused.length > 1 ? 'two' : 'one'][toRandom ? 'toRandom' : 'kept']
      text.push(m[key]({ models: list(paused), until: reset.until }))
      why.push(m[pause.network ? 'arene.limits.picked.whyNetwork' : 'arene.limits.picked.why']())
    }
    return { reset, text: text.join(' '), why: why.join(' ') }
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
