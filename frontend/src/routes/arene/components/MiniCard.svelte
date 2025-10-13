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
  } & SvelteHTMLElements['div'] = $props()
</script>

<div {...props} class={['cg-border rounded-sm! relative p-3', props.class]}>
  <Tooltip id="mini-card-tooltip-{id}" size="sm" class="absolute right-1.5 top-1">
    {@html sanitize(tooltip)}
  </Tooltip>

  <div class={[icon ? 'flex flex-col items-center gap-2 md:flex-row md:gap-3' : '']}>
    {#if icon}
      <Icon {icon} block class={iconClass} />
    {/if}
    <div class={[icon ? 'text-center md:text-start' : '']}>
      <strong class="inline-flex items-baseline leading-normal">
        <span class={[icon ? 'text-[24px]' : 'text-[18px]']}>{value}</span>
        <span class={[icon ? 'text-[14px]' : 'ms-1 text-[10px]']}>
          {#if units}
            {@html sanitize(units)}
          {:else}
            {@render children?.()}
          {/if}
        </span>
      </strong>
      <p class="text-sm! mb-0! -mt-1! leading-normal">{@html sanitize(desc)}</p>
    </div>
  </div>
</div>
