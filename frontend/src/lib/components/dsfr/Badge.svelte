<script lang="ts">
  import { Tooltip } from '$components/dsfr'
  import type { SvelteHTMLElements } from 'svelte/elements'

  export type BadgeProps = {
    id?: string
    size?: 'xs' | 'sm' | 'md'
    variant?:
      | ''
      | 'info'
      | 'light-info'
      | 'green'
      | 'orange'
      | 'yellow'
      | 'green-tilleul'
      | 'purple'
      | 'red'
      | 'blue-ecume'
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
    'light-info': 'light-info',
    green: 'green-emeraude',
    'green-tilleul': 'green-tilleul-verveine',
    orange: 'orange-terre-battue',
    yellow: 'yellow-tournesol',
    purple: 'purple-glycine',
    red: 'error',
    'blue-ecume': 'blue-ecume'
  } as const
</script>

<span
  {...props}
  {id}
  class={[
    `fr-badge fr-badge--${variants[variant]} fr-badge--${size} fr-badge--no-icon`,
    { 'text-xs!': size === 'xs', 'py-1!': size === 'md' },
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

<style>
  .fr-badge--light-info {
    background-color: var(--color-light-info);
    color: var(--color-info);
  }
</style>
