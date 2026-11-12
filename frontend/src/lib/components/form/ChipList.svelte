<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { tick } from 'svelte'
  import type { ClassValue } from 'svelte/elements'

  let {
    label,
    items,
    disabled = false,
    onremove,
    onempty,
    class: classes
  }: {
    /** Names the list for screen readers. */
    label: string
    items: { value: string; label: string }[]
    disabled?: boolean
    onremove: (value: string) => void
    class?: ClassValue
    /** Where focus goes once the last chip is removed. */
    onempty?: () => void
  } = $props()

  let list = $state<HTMLUListElement>()

  // The button just pressed goes away with its chip: focus moves to the chip
  // that took its place, so a keyboard user does not land back at the top.
  async function remove(index: number) {
    onremove(items[index].value)
    await tick()
    const buttons = list?.querySelectorAll('button') ?? []
    const next = buttons[Math.min(index, buttons.length - 1)]
    if (next) next.focus()
    else onempty?.()
  }
</script>

{#if items.length}
  <ul
    bind:this={list}
    class={['gap-2 m-0! p-0! flex list-none flex-wrap', classes]}
    aria-label={label}
  >
    {#each items as item, index (item.value)}
      <li
        class="gap-1 ps-3 pe-1 py-0.5 text-sm min-w-0 flex items-center rounded-full bg-[--background-contrast-grey]"
      >
        <span class="min-w-0 break-words">{item.label}</span>
        <button
          type="button"
          class="p-1 inline-flex shrink-0 rounded-full hover:bg-[--background-contrast-grey-hover]"
          aria-label={m['form.tags.remove']({ tag: item.label })}
          title={m['form.tags.remove']({ tag: item.label })}
          {disabled}
          onclick={() => remove(index)}
        >
          <span class="i-ri-close-line size-4" aria-hidden="true"></span>
        </button>
      </li>
    {/each}
  </ul>
{/if}
