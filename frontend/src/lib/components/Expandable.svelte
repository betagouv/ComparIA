<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'
  import type { SvelteSet } from 'svelte/reactivity'

  let {
    id,
    label,
    content,
    expanded = $bindable(false),
    labelClass,
    contentClass,
    ...props
  }: {
    id: string
    label: string | Snippet
    content: string | Snippet
    expanded?: boolean | SvelteSet<string>
    labelClass?: ClassValue
    contentClass?: ClassValue
  } & SvelteHTMLElements['div'] = $props()

  const opened = $derived(typeof expanded === 'boolean' ? expanded : expanded.has(id))

  function toggle() {
    if (typeof expanded === 'boolean') expanded = !expanded
    else if (expanded.has(id)) expanded.delete(id)
    else expanded.add(id)
  }
</script>

<div {...props}>
  <button
    type="button"
    aria-expanded={opened}
    aria-controls={id}
    onclick={() => toggle()}
    class={['gap-1 flex items-center text-start', labelClass]}
  >
    {#if typeof label === 'string'}{label}{:else}{@render label()}{/if}
    <Icon
      icon="i-ri-arrow-right-s-line"
      size="sm"
      block
      class={['text-primary', { 'rotate-90': opened }]}
    />
  </button>

  {#if opened}
    <div {id} class={['mt-1', contentClass]}>
      {#if typeof content === 'string'}{content}{:else}{@render content()}{/if}
    </div>
  {/if}
</div>
