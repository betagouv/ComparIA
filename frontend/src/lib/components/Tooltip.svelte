<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { Snippet } from 'svelte'

  export interface TooltipProps {
    id: string
    size?: 'xs' | 'sm' | 'md'
    text?: string
    label?: string
    children?: Snippet
  }

  let { id, text, label, children, size = 'sm' }: TooltipProps = $props()
</script>

<a class="fr-icon fr-icon-question-line fr-icon--{size}" aria-describedby={id} href="#{id}">
  <span class="sr-only">{label ?? m['words.tooltip']()}</span>
</a>
<span {id} class="fr-tooltip fr-placement font-normal normal-case" role="tooltip">
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
