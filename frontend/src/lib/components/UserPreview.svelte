<script lang="ts">
  import { MarkdownCode as Markdown } from '$components/markdown'
  import { m } from '$lib/i18n/messages'
  import type { Snippet } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    content,
    ratio = 'md',
    children,
    contentSnippet,
    ...props
  }: {
    id: string
    content?: string
    ratio?: 'sm' | 'md'
    contentSnippet?: Snippet
  } & SvelteHTMLElements['div'] = $props()

  const grid = $derived(
    {
      sm: { main: 'lg:basis-3/5', aside: 'lg:basis-2/5' },
      md: { main: 'lg:basis-1/2', aside: 'lg:basis-1/2' }
    }[ratio]
  )
</script>

<div {id} {...props} class={['gap-6 xl:flex-row flex flex-col items-stretch', props.class]}>
  <div class={grid.main}>
    {@render children?.()}
  </div>

  <aside class={grid.aside}>
    <h2 id="{id}-title" class="text-sm! mb-4! text-[--green-tilleul-verveine-sun-418-moon-817]">
      {m['form.preview']()}
    </h2>

    <div class="p-5 bg-[--green-tilleul-verveine-975-75]">
      {#if contentSnippet}
        {@render contentSnippet()}
      {:else if content}
        <Markdown message={content} sanitize_html variant="document" />
      {:else}
        <p class="fr-text--sm">{m['form.previewEmpty']()}</p>
      {/if}
    </div>
  </aside>
</div>
