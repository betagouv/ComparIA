<script
  lang="ts"
  generics="T extends {id?: string; label: string; content: string, class?: ClassValue}"
>
  import { Accordion } from '$components/dsfr'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    items,
    children,
    group = true,
    markdown = false,
    ...props
  }: {
    id: string
    items?: T[]
    group?: boolean
    markdown?: boolean
  } & SvelteHTMLElements['div'] = $props()
</script>

<div {id} data-fr-group={group ? 'true' : 'false'} class="fr-accordions-group" {...props}>
  {#if items}
    {#each items as item, i (i)}
      <Accordion
        id="{id}-{item.id ?? i.toString()}"
        label={item.label}
        content={item.content}
        class={item.class}
        {markdown}
      />
    {/each}
  {:else}
    {@render children?.()}
  {/if}
</div>
