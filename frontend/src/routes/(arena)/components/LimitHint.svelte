<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { focusOnShow } from '$lib/helpers/attachments'
  import type { ClassValue } from 'svelte/elements'

  let {
    id,
    text,
    icon,
    focusOnShow: focus = false,
    class: className
  }: {
    id: string
    text: string
    icon: string
    /** It answers a send that did not start: focus it, or nothing tells why. */
    focusOnShow?: boolean
    class?: ClassValue
  } = $props()
</script>

<p
  {id}
  class={['cl-limit-hint fr-text--sm gap-2 mb-0! flex', className]}
  {@attach focusOnShow(() => focus)}
>
  <Icon {icon} size="sm" block class="text-primary mt-0.5 shrink-0" />
  <span>{text}</span>
</p>

<style>
  .cl-limit-hint {
    color: var(--text-mention-grey);
  }
</style>
