<script lang="ts" module>
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { resetTime, spoken } from './resetTime'

  /** What the home form changed, or cannot do, before anyone sends. */
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
      }
    | { kind: 'mode'; until: string | null }

  function copy(pause: PickPause) {
    const reset = resetTime(pause.until)
    if (pause.kind === 'mode')
      return { reset, text: m['arene.limits.mode.choose']({ at: reset.at }) }
    const models = new Intl.ListFormat(getLocale(), { type: 'conjunction' }).format(pause.names)
    if (pause.full) return { reset, text: m['arene.limits.picker.trimmedFull']({ models }) }
    const key =
      pause.names.length > 1 ? 'arene.limits.picker.trimmedTwo' : 'arene.limits.picker.trimmedOne'
    return { reset, text: m[key]({ models, at: reset.at }) }
  }

  /** The notice as a screen reader hears it, for the form's live region. */
  export function pickPauseSaid(pause: PickPause): string {
    const { reset, text } = copy(pause)
    const line = spoken(text, reset)
    if (pause.kind === 'mode') return `${m['arene.limits.mode.title']()}. ${line}`
    return pause.toRandom ? `${line} ${m['arene.limits.picked.toRandom']()}` : line
  }
</script>

<script lang="ts">
  import { Alert } from '$components/dsfr'
  import TimedText from './TimedText.svelte'

  let { pause }: { pause: PickPause } = $props()

  const { reset, text } = $derived(copy(pause))
</script>

{#if pause.kind === 'mode'}
  <Alert id="pick-paused-notice" title={m['arene.limits.mode.title']()} class="w-full">
    <p><TimedText {text} {reset} /></p>
  </Alert>
{:else}
  {#snippet title()}
    <TimedText {text} {reset} />
  {/snippet}
  <Alert id="pick-paused-notice" {title} small class="w-full">
    {#if pause.toRandom}
      <p>{m['arene.limits.picked.toRandom']()}</p>
    {/if}
  </Alert>
{/if}
