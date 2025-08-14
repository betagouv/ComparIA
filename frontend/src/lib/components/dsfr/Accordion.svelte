<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label,
    content,
    children,
    ...props
  }: {
    id: string
    label: string
    content?: string
  } & SvelteHTMLElements['section'] = $props()
</script>

<section class="fr-accordion" {...props}>
  <h3 class="fr-accordion__title">
    <button
      type="button"
      class="fr-accordion__btn"
      aria-expanded="false"
      aria-controls={`accordion-${id}`}
    >
      {label}
    </button>
  </h3>
  <div class="fr-collapse" id={`accordion-${id}`}>
    {#if content}{content}{:else}{@render children?.()}{/if}
  </div>
</section>
