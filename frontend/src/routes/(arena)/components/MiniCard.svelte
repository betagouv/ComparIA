<script lang="ts">
  import { Icon, Tooltip } from '$components/dsfr'
  import { sanitize } from '$lib/utils/commons'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    value,
    desc,
    tooltip,
    units,
    icon,
    iconClass,
    compact = false,
    children,
    ...props
  }: {
    id: string
    value: number | string
    desc: string
    tooltip: string
    units?: string
    icon?: string
    iconClass?: ClassValue
    compact?: boolean
  } & SvelteHTMLElements['div'] = $props()
</script>

<div {...props} class={['cg-border rounded-sm! p-3 min-w-0 relative', props.class]}>
  <Tooltip
    id="mini-card-tooltip-{id}"
    size={compact ? 'xs' : 'sm'}
    class="top-1 right-1.5 absolute"
  >
    {@html sanitize(tooltip)}
  </Tooltip>

  <div
    class={[
      icon
        ? compact
          ? 'gap-1 min-w-0 flex w-full flex-col items-center'
          : 'gap-2 md:flex-row md:gap-3 flex flex-col items-center'
        : ''
    ]}
  >
    {#if icon}
      <Icon {icon} size={compact ? 'sm' : 'md'} block class={iconClass} />
    {/if}
    <div class={[icon ? (compact ? 'min-w-0 text-center' : 'md:text-start text-center') : '']}>
      <strong class="leading-normal inline-flex max-w-full items-baseline">
        <span
          class={[icon ? (compact ? 'text-base whitespace-nowrap' : 'text-[24px]') : 'text-[18px]']}
        >
          {value}
        </span>
        <span
          class={[
            icon ? (compact ? 'ms-0.5 text-[10px]' : 'ms-1 text-[14px]') : 'ms-1 text-[10px]'
          ]}
        >
          {#if units}
            {@html sanitize(units)}
          {:else}
            {@render children?.()}
          {/if}
        </span>
      </strong>
      <p class={['-mt-1! mb-0! leading-normal', compact ? 'text-xxs! break-words' : 'text-sm!']}>
        {@html sanitize(desc)}
      </p>
    </div>
  </div>
</div>
