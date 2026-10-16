<script lang="ts">
  import { Icon, Toggletip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { focusOnShow } from '$lib/helpers/attachments'
  import type { ClassValue } from 'svelte/elements'
  import type { ResetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    id,
    text,
    reset,
    why,
    icon,
    focusOnShow: focus = false,
    class: className
  }: {
    id: string
    /** One sentence, with TIME_SLOT where the clock time goes, if any. */
    text: string
    reset?: ResetTime
    /** Left out, it is a helper line, as quiet as the text box's own hint. */
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
  class={[
    'cl-limit-hint mb-0! relative',
    icon ? 'fr-text--sm gap-2 flex' : 'fr-message',
    className
  ]}
  {@attach focusOnShow(() => focus)}
>
  {#if icon}
    <Icon {icon} size="sm" block class="text-primary mt-0.5 shrink-0" />
  {/if}
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
