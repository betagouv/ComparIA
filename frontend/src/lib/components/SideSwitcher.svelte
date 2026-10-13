<script lang="ts">
  import { Button } from '$components/dsfr'
  import type { Bot } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { onDestroy } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let { children, ...props }: SvelteHTMLElements['div'] = $props()

  let scrolledSide = $state<Bot>('a')
  let scrollableElem = $state<HTMLDivElement>()

  function scrollToSide(side: Bot) {
    scrollableElem?.scrollTo({
      left: side === 'b' ? scrollableElem.scrollWidth : 0,
      behavior: 'smooth'
    })
    scrolledSide = side
  }

  function doScroll() {
    scrollToSide(scrolledSide === 'a' ? 'b' : 'a')
  }

  // Keep keyboard focus on screen: show the side holding the focused element
  function onFocusIn(event: FocusEvent) {
    if (!scrollableElem || scrollableElem.scrollWidth <= scrollableElem.clientWidth) return
    const sides = Array.from(scrollableElem.firstElementChild?.children ?? [])
    const index = sides.findIndex((side) => side.contains(event.target as Node))
    if (index !== -1) scrollToSide(index === 0 ? 'a' : 'b')
  }

  let scrollDebounce: ReturnType<typeof setTimeout> | undefined
  function onScroll() {
    if (!scrollableElem) return
    clearTimeout(scrollDebounce)
    scrollDebounce = setTimeout(() => {
      if (!scrollableElem) return
      const { scrollLeft, scrollWidth, clientWidth } = scrollableElem
      const maxScroll = scrollWidth - clientWidth
      if (maxScroll <= 0) return
      const next: Bot = scrollLeft / maxScroll > 0.5 ? 'b' : 'a'
      if (next !== scrolledSide) scrolledSide = next
    }, 80)
  }

  onDestroy(() => clearTimeout(scrollDebounce))
</script>

<div {...props} class="min-h-0 relative flex max-w-full">
  <div
    class="cl-side-switcher-scroller md:overflow-hidden! flex w-full overflow-x-auto"
    bind:this={scrollableElem}
    onscroll={onScroll}
    onfocusin={onFocusIn}
  >
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

<style>
  @media (max-width: 47.99em) {
    .cl-side-switcher-scroller {
      scroll-snap-type: x mandatory;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }
    .cl-side-switcher-scroller::-webkit-scrollbar {
      display: none;
    }
    .cl-side-switcher-scroller :global(> * > *) {
      scroll-snap-align: center;
      scroll-snap-stop: always;
    }
  }
</style>
