<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import type { BotModel } from '$lib/models'
  import type { ClassValue } from 'svelte/elements'

  let {
    cx,
    cy,
    r,
    model,
    class: className,
    onpointerenter,
    onpointerleave
  }: {
    cx: number
    cy: number
    r: number
    model: Pick<BotModel, 'lab'>
    class?: ClassValue
    onpointerenter: () => void
    onpointerleave: () => void
  } = $props()

  // Logo diameter, leaving a ring of the dot's colour around it.
  const logo = $derived(Math.max(r * 2 - 6, 8))
</script>

<!-- The circle takes the pointer; the logo above it lets events through so
     hovering the lab mark still reads as hovering the model. -->
<circle {cx} {cy} {r} class={className} aria-hidden="true" {onpointerenter} {onpointerleave} />
<foreignObject
  x={cx - logo / 2}
  y={cy - logo / 2}
  width={logo}
  height={logo}
  class="pointer-events-none"
  aria-hidden="true"
>
  <div
    xmlns="http://www.w3.org/1999/xhtml"
    class="logo-box flex h-full w-full items-center justify-center"
  >
    <AILogo
      logo={model.lab.logo}
      customLogoId={model.lab.has_custom_logo ? model.lab.id : undefined}
      alt=""
    />
  </div>
</foreignObject>

<style lang="postcss">
  /* AILogo sizes come as fixed classes; the dot decides the size here. */
  .logo-box :global(img),
  .logo-box :global(span) {
    width: 100% !important;
    height: 100% !important;
  }
</style>
