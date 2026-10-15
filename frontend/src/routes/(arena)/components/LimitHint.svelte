<script lang="ts">
  import { Icon, Toggletip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { focusOnShow } from '$lib/helpers/attachments'
  import type { ClassValue } from 'svelte/elements'
  import { PAUSED_ICON } from '$lib/limits.svelte'
  import type { ResetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    id,
    text,
    reset,
    why,
    icon = PAUSED_ICON,
    focusOnShow: focus = false,
    class: className
  }: {
    id: string
    /** One sentence, with TIME_SLOT where the clock time goes, if any. */
    text: string
    reset?: ResetTime
    /** The state's icon: paused for the person, full for the day, or busy. */
    icon?: string
    /** What "Pourquoi ?" opens. */
    why?: string
    /** It answers a send that did not start: focus it, or nothing tells why. */
    focusOnShow?: boolean
    class?: ClassValue
  } = $props()
</script>

<p
  {id}
  class={['cl-limit-hint fr-text--sm mb-0! gap-2 relative flex', className]}
  {@attach focusOnShow(() => focus)}
>
  <Icon {icon} size="sm" block class="text-primary mt-0.5 shrink-0" />
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
