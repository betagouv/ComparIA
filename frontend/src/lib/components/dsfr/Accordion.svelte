<script lang="ts">
  import MarkdownCode from '$components/markdown/MarkdownCode.svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label,
    content,
    class: klass,
    markdown,
    children,
    ...props
  }: {
    id: string
    label: string
    content?: string
    class?: ClassValue
    markdown?: boolean
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
  <div class={['fr-collapse m-0!', klass]} id={`accordion-${id}`}>
    {#if content}
      {#if markdown}
        <MarkdownCode message={content} sanitize_html variant="document" />
      {:else}
        {content}
      {/if}
    {:else}
      {@render children?.()}
    {/if}
  </div>
</section>
