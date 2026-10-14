<script lang="ts">
  import { Icon, Toggletip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'
  import type { ClassValue } from 'svelte/elements'
  import type { ResetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    id,
    text,
    reset,
    why,
    focusOnShow = false,
    class: className
  }: {
    id: string
    /** One sentence, with TIME_SLOT where the clock time goes. */
    text: string
    reset: ResetTime
    /** What "Pourquoi ?" opens. */
    why?: string
    /** It answers a send that did not start: focus it, or nothing tells why. */
    focusOnShow?: boolean
    class?: ClassValue
  } = $props()

  let el = $state<HTMLParagraphElement>()

  onMount(() => {
    if (!focusOnShow || !el) return
    el.tabIndex = -1
    el.focus()
  })
</script>

<p bind:this={el} {id} class={['cl-limit-hint fr-text--sm mb-0! gap-2 relative flex', className]}>
  <Icon icon="i-ri-pause-circle-line" size="sm" block class="text-primary mt-0.5 shrink-0" />
  <span>
    <TimedText {text} {reset} />
    {#if why}
      <Toggletip id="{id}-why" label={m['arene.limits.why']()} text={why} class="ms-1" />
    {/if}
  </span>
</p>

<style>
  .cl-limit-hint {
    color: var(--text-mention-grey);
  }
</style>
