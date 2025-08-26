<script lang="ts" generics="T extends {id?: string; label: string; content: string}">
  import { Accordion } from '$components/dsfr'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let { items, children, ...props }: { items?: T[] } & SvelteHTMLElements['div'] = $props()
</script>

<div data-fr-group="true" class="fr-accordions-group" {...props}>
  {#if items}
    {#each items as item, i}
      <Accordion id={item.id ?? i.toString()} label={item.label} content={item.content} />
    {/each}
  {:else}
    {@render children?.()}
  {/if}
</div>
