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
  let bubble = $state<HTMLElement>()
  // Where the bubble starts, so it opens under its button rather than at the
  // start of the line. Kept inside the line's width.
  let start = $state(0)

  $effect(() => {
    if (!open || !button || !bubble) return
    const line = bubble.offsetParent as HTMLElement | null
    if (!line) return
    start = Math.max(0, Math.min(button.offsetLeft, line.clientWidth - bubble.offsetWidth))
  })

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

  // Tabbing away closes it too, or it would cover what focus moved to.
  function onFocusOut(e: FocusEvent) {
    if (open && !wrapper?.contains(e.relatedTarget as Node | null)) open = false
  }
</script>

<svelte:window onkeydown={onWindowKeydown} onclick={onWindowClick} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span
  bind:this={wrapper}
  class={['cl-toggletip', className]}
  onkeydown={onKeydown}
  onfocusout={onFocusOut}
>
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
      <span
        bind:this={bubble}
        class="cl-toggletip__bubble fr-text--sm"
        style:--cl-toggletip-start="{start}px"
      >
        {#if typeof text === 'string'}{text}{:else}{@render children?.()}{/if}
      </span>
    {/if}
  </span>
</span>

<style>
  /* Underlined, as DSFR links are, so it does not read as a link by its
     colour alone (WCAG 1.4.1). The padding gives a 44px tap area without
     moving the text; the background stays clear on hover, for contrast. */
  .cl-toggletip__button {
    --idle: transparent;
    --hover: transparent;
    --active: transparent;
    padding: 0.625rem 0;
    margin-block: -0.625rem;
    font-size: inherit;
    line-height: inherit;
    background-image: none;
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 0.2em;

    &:hover {
      text-decoration-thickness: 2px;
    }
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

  /* Below it, the bubble takes the whole line. */
  @media (min-width: 48em) {
    .cl-toggletip__bubble {
      inset-inline: var(--cl-toggletip-start, 0) auto;
      width: min(24rem, 100%);
    }
  }
</style>
