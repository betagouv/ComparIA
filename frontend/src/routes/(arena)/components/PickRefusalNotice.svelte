<script lang="ts">
  import { Alert } from '$components/dsfr'
  import type { PickRefusal } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { resetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    refusal,
    names
  }: {
    refusal: PickRefusal
    /** The names of the picked models the person may not use yet, if any. */
    names: string[]
  } = $props()

  const reset = $derived(resetTime(refusal.limit.resets_at))
  const title = $derived(
    names.length
      ? m['arene.limits.picked.title']({
          models: new Intl.ListFormat(getLocale(), { type: 'conjunction' }).format(names)
        })
      : m['arene.limits.mode.title']()
  )
</script>

<!-- Sent from the text box, which stays: without focusTitle a screen reader
     would not hear why nothing started. -->
<Alert id="pick-refusal-notice" {title} focusTitle class="w-full">
  {#if names.length}
    <p>
      <TimedText
        text={m[names.length > 1 ? 'arene.limits.picked.backTwo' : 'arene.limits.picked.backOne']({
          at: reset.at
        })}
        {reset}
      />
    </p>
    <p>
      {m[
        refusal.limit.scope === 'network'
          ? 'arene.limits.picked.whyNetwork'
          : 'arene.limits.picked.why'
      ]()}
    </p>
    <p>{m['arene.limits.picked.resend']()}</p>
  {:else}
    <p><TimedText text={m['arene.limits.mode.back']({ at: reset.at })} {reset} /></p>
  {/if}
</Alert>
