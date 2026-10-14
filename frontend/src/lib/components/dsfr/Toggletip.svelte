<script lang="ts">
  import type { Snippet } from 'svelte'
  import type { ClassValue } from 'svelte/elements'

  let {
    id,
    label,
    text,
    children,
    class: className
  }: {
    id: string
    /** The button that opens it, such as "Pourquoi ?". */
    label: string
    text?: string
    children?: Snippet
    class?: ClassValue
  } = $props()

  let open = $state(false)
  let wrapper = $state<HTMLElement>()
  let button = $state<HTMLButtonElement>()

  // A tooltip shows on hover and cannot hold a sentence a phone user can
  // reach, so this opens on a click or Enter and stays until dismissed.
  function onWindowKeydown(e: KeyboardEvent) {
    if (open && e.key === 'Escape') {
      open = false
      button?.focus()
    }
  }

  // An Escape meant for it must not also close a dialog it sits in. A DSFR
  // modal hears the key first, on the document, and leaves it to an open
  // tooltip: the button says it is one while open.
  function onKeydown(e: KeyboardEvent) {
    if (!open || e.key !== 'Escape') return
    // A native <dialog> closes on the key's default action.
    e.preventDefault()
    e.stopPropagation()
    onWindowKeydown(e)
  }

  function onWindowClick(e: MouseEvent) {
    if (open && !wrapper?.contains(e.target as Node)) open = false
  }
</script>

<svelte:window onkeydown={onWindowKeydown} onclick={onWindowClick} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span bind:this={wrapper} class={['cl-toggletip', className]} onkeydown={onKeydown}>
  <button
    bind:this={button}
    type="button"
    class="fr-link fr-text--sm cl-toggletip__button"
    aria-expanded={open}
    aria-controls={id}
    data-fr-js-tooltip-referent={open ? '' : undefined}
    onclick={() => (open = !open)}
  >
    {label}
  </button>
  <!-- A live region from first render: what lands in it on opening is read
       out, without moving focus. Placed under the nearest positioned parent. -->
  <span {id} role="status" class="cl-toggletip__region">
    {#if open}
      <span class="cl-toggletip__bubble fr-text--sm">
        {#if typeof text === 'string'}{text}{:else}{@render children?.()}{/if}
      </span>
    {/if}
  </span>
</span>

<style>
  .cl-toggletip__button {
    padding: 0;
    font-size: inherit;
    line-height: inherit;
  }

  .cl-toggletip__bubble {
    position: absolute;
    top: calc(100% + 0.5rem);
    inset-inline: 0;
    z-index: 10;
    display: block;
    max-width: 24rem;
    margin: 0 !important;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    background-color: var(--background-overlap-grey);
    color: var(--text-default-grey);
    box-shadow: var(--overlap-shadow);
    text-align: start;
    font-weight: 400;
  }
</style>
