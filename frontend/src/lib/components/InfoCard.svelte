<script lang="ts">
  import { Badge, Icon, Tooltip } from '$components/dsfr'
  import type { ModelCardSize } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'
  import type { BadgeProps } from './dsfr/Badge.svelte'

  let {
    id,
    title,
    titleTag = 'h2',
    titleClass,
    icon,
    iconClass,
    badge,
    tooltip,
    content,
    subContent,
    contentTag = 'div',
    desc,
    size = 'md',
    children,
    ...props
  }: {
    id: string
    icon: string
    title: string
    titleTag?: string
    titleClass?: ClassValue
    iconClass?: ClassValue
    badge?: BadgeProps
    tooltip?: string
    content?: string
    subContent?: string
    contentTag?: string
    desc?: string
    size?: ModelCardSize
  } & SvelteHTMLElements['div'] = $props()

  const classes = $derived(
    (
      {
        xs: { base: 'p-2 gap-1', title: 'text-xxs!', content: '', sub: 'text-sm!', icon: 'xxs' },
        sm: {
          base: 'p-3 gap-3',
          title: 'text-xxs!',
          content: 'text-lg!',
          sub: 'text-xxs!',
          icon: 'xs'
        },
        md: {
          base: 'p-4 gap-2',
          title: 'text-sm!',
          content: 'text-[22px]!',
          sub: 'text-sm!',
          icon: 'xs'
        }
      } as const
    )[size]
  )
</script>

{#snippet innerContent(content: string, subContent?: string)}
  <div>
    <p class={['mb-0! font-bold leading-[1.1]!', classes.content]}>
      {@html sanitize(content)}
    </p>
    {#if subContent && size !== 'xs'}
      <p class={['text-grey mb-0!', classes.sub]}>
        {@html sanitize(subContent)}
      </p>
    {/if}
  </div>
{/snippet}

<article {id} class={['cg-border bg-white flex flex-col', classes.base, props.class]}>
  <div class="gap-1 flex">
    <svelte:element
      this={titleTag}
      class={['gap-1 font-normal mb-0! p-0! min-w-0 flex items-center', classes.title, titleClass]}
    >
      <Icon {icon} size={classes.icon} block class={size !== 'xs' ? iconClass : undefined} />
      {title}
    </svelte:element>

    {#if size !== 'xs'}
      <div class="gap-1 ms-auto flex shrink-0 items-center">
        {#if badge}
          <Badge {...badge} size="sm" />
        {/if}
        {#if tooltip}
          <Tooltip id="tooltip-{id}" size="xs" class="lh-none! block!">
            {@html sanitize(tooltip)}
          </Tooltip>
        {/if}
      </div>
    {/if}
  </div>

  <svelte:element this={contentTag} class="">
    {#if content}
      {@render innerContent(content, subContent)}
    {:else if badge && size === 'xs'}
      <Badge {...badge} tooltip={undefined} size="sm" />
    {:else}
      {@render children?.()}
    {/if}
  </svelte:element>

  {#if desc && size === 'md'}
    <p class="bg-very-light-primary text-xxs p-1 mb-0! b-light-primary rounded-sm mt-auto! border">
      {desc}
    </p>
  {/if}
</article>
