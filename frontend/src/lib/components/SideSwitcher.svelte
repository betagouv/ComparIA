<script lang="ts">
  import { Button } from '$components/dsfr'
  import type { Bot } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let { children, ...props }: SvelteHTMLElements['div'] = $props()

  let scrolledSide = $state<Bot>('a')
  let scrollableElem = $state<HTMLDivElement>()

  function doScroll() {
    scrollableElem?.scrollTo({ left: scrolledSide === 'a' ? scrollableElem?.scrollWidth : 0 })
    scrolledSide = scrolledSide === 'a' ? 'b' : 'a'
  }
</script>

<div {...props} class="min-h-0 relative flex max-w-full">
  <div class="flex w-full overflow-hidden" bind:this={scrollableElem}>
    {@render children?.()}
  </div>

  {#each ['a', 'b'] as const as pos (pos)}
    <Button
      text={m[pos === 'b' ? 'actions.scrollRight' : 'actions.scrollLeft']()}
      icon={pos === 'b' ? 'arrow-right-line' : 'arrow-left-line'}
      iconOnly
      variant="tertiary"
      class={[
        'bg-white! md:hidden! absolute top-1/2 inline-flex -translate-y-1/2',
        { 'hidden!': pos === scrolledSide, 'left-0': pos === 'a', 'right-0': pos === 'b' }
      ]}
      onclick={() => doScroll()}
    />
  {/each}
</div>
