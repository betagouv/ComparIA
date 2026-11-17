<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { Tool } from '$lib/global.svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    tool,
    size = 'sm',
    ...props
  }: { tool: Omit<Tool, 'enabled'>; size?: 'xs' | 'sm' } & SvelteHTMLElements['div'] = $props()
</script>

<div {...props} class={['gap-2 bg-white flex', `text-${size}`, props.class]}>
  <div
    class={['b-1 rounded-sm flex border-[--grey-925-125]', size === 'sm' ? 'h-8 w-8' : 'h-5 w-5']}
  >
    <Icon icon={tool.icon} src={tool.logo_url} class="text-primary m-auto" {size} block />
  </div>

  <div class="lh-tight! h-fit place-self-center">
    <strong>{tool.label}</strong><br />
    {#if size == 'sm' && tool.description}
      <span class="text-grey text-[11px]">{tool.description}</span>
    {/if}
  </div>
</div>
