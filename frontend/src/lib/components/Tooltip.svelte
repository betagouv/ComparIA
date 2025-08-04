<script lang="ts">
  import { teleport } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import type { Snippet } from 'svelte'

  export interface TooltipProps {
    id: string
    size?: 'xs' | 'sm' | 'md'
    text?: string
    label?: string
    teleportId?: string
    children?: Snippet
  }

  let { id, text, label, children, teleportId = 'tooltips', size = 'sm' }: TooltipProps = $props()
</script>

<a class="fr-icon fr-icon-question-line fr-icon--{size}" aria-describedby={id} href="#{id}">
  <span class="sr-only">{label ?? m['words.tooltip']()}</span>
</a>
<span
  {id}
  class="fr-tooltip fr-placement font-normal normal-case"
  role="tooltip"
  {@attach teleport(teleportId)}
>
  {#if typeof text === 'string'}
    {text}
  {:else}
    {@render children?.()}
  {/if}
</span>

<style>
  a {
    /* Remove DSFR underline */
    --underline-img: 0;
  }
</style>
