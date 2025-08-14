<script lang="ts">
  import Tooltip from '$components/Tooltip.svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  export type BadgeProps = {
    id: string
    size?: 'xs' | 'sm' | 'md'
    variant?: '' | 'info' | 'green' | 'orange' | 'yellow'
    text?: string
    tooltip?: string
  } & SvelteHTMLElements['span']

  let { id, variant = '', text, size = 'md', tooltip, children, ...props }: BadgeProps = $props()

  const variants = {
    '': '',
    info: 'info',
    green: 'green-emeraude',
    orange: 'orange-terre-battue',
    yellow: 'yellow-tournesol'
    // FIXME red
  } as const
</script>

<span
  {...props}
  {id}
  class={[
    `fr-badge fr-badge--${variants[variant]} fr-badge--${size} fr-badge--no-icon`,
    props.class
  ]}
>
  {#if typeof text === 'string'}
    {text}
    {#if tooltip}
      <Tooltip id="{id}-tooltip" size="xs" text={tooltip} class="ms-1" />
    {/if}
  {:else}
    {@render children?.()}
  {/if}
</span>
