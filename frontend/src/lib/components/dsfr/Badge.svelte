<script lang="ts">
  import { Tooltip } from '$components/dsfr'
  import type { SvelteHTMLElements } from 'svelte/elements'

  export type BadgeProps = {
    id?: string
    size?: 'xs' | 'sm' | 'md'
    variant?: '' | 'info' | 'green' | 'orange' | 'yellow' | 'purple' | 'red'
    text?: string
    tooltip?: string
    noTooltip?: boolean
  } & SvelteHTMLElements['span']

  let {
    id,
    variant = '',
    text,
    size = 'md',
    tooltip,
    noTooltip = false,
    children,
    ...props
  }: BadgeProps = $props()

  const variants = {
    '': '',
    info: 'info',
    green: 'green-emeraude',
    orange: 'orange-terre-battue',
    yellow: 'yellow-tournesol',
    purple: 'purple-glycine',
    red: 'error'
  } as const
</script>

<span
  {...props}
  {id}
  class={[
    `fr-badge fr-badge--${variants[variant]} fr-badge--${size} fr-badge--no-icon`,
    { 'text-xs!': size === 'xs' },
    props.class
  ]}
>
  {#if typeof text === 'string'}
    {text}
    {#if tooltip && !noTooltip}
      <Tooltip id="{id}-tooltip" size="xs" text={tooltip} class="ms-1" />
    {/if}
  {:else}
    {@render children?.()}
  {/if}
</span>
