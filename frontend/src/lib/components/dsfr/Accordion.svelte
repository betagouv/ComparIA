<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label,
    content,
    level = 3,
    children,
    ...props
  }: {
    id: string
    label: string
    content?: string
    /** The title's heading level, to fit the page's outline. */
    level?: 2 | 3 | 4
  } & SvelteHTMLElements['section'] = $props()
</script>

<section class="fr-accordion" {...props}>
  <svelte:element this={`h${level}`} class="fr-accordion__title">
    <button
      type="button"
      class="fr-accordion__btn"
      aria-expanded="false"
      aria-controls={`accordion-${id}`}
    >
      {label}
    </button>
  </svelte:element>
  <div class="fr-collapse" id={`accordion-${id}`}>
    {#if content}{content}{:else}{@render children?.()}{/if}
  </div>
</section>
