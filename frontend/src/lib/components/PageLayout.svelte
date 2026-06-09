<script lang="ts">
  import SeoHead from '$components/SEOHead.svelte'
  import type { Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  let {
    seoTitle,
    title,
    subtitle,
    bubble,
    stickyHeader = false,
    headerClass,
    header,
    children,
    ...props
  }: {
    seoTitle: string
    title: string
    subtitle?: string
    bubble?: string
    stickyHeader?: boolean
    headerClass?: ClassValue
    header?: Snippet
  } & SvelteHTMLElements['div'] = $props()

  // Compute page header height for autoscrolling
  let headerElem = $state<HTMLElement>()
  let headerElemSize = $derived<number>(headerElem?.offsetHeight ?? 0)

  function onResize() {
    headerElemSize = headerElem ? headerElem.offsetHeight : 0
  }
  $effect(() => {
    // Recomputed on header class change
    if (headerClass || !headerClass) onResize()
  })
</script>

<svelte:window onresize={onResize} />

<SeoHead title={seoTitle} />

<header
  bind:this={headerElem}
  id="second-header"
  class={[
    'bg-very-light-primary py-3 md:py-4 px-4 md:px-6 relative z-3 drop-shadow-[--raised-shadow]',
    { 'top-0 sticky!': stickyHeader },
    headerClass
  ]}
>
  <div class="gap-3 md:flex-row flex flex-col items-center">
    {#if bubble}
      <div class="bg-primary px-4 py-2 font-bold text-white rounded-[3.75rem] text-nowrap">
        {bubble}
      </div>
    {/if}

    <div class="md:text-left flex flex-col text-center">
      <h1 class="text-base mb-0">{title}</h1>
      {#if subtitle}
        <p class="m-0! text-sm! leading-normal! text-grey">{subtitle}</p>
      {/if}
    </div>

    {@render header?.()}
  </div>
</header>

<div
  {...props}
  class={['px-4 md:px-6 py-6', props.class]}
  style="--second-header-size: {headerElemSize}px;"
>
  {@render children?.()}
</div>
