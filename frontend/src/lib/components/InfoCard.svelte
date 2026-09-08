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
    rootTag = 'article',
    titleClass,
    icon,
    iconClass,
    badge,
    contentBadge,
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
    /** Inside a <dl> an <article> is invalid markup; pass 'div' there. */
    rootTag?: string
    titleClass?: ClassValue
    iconClass?: ClassValue
    badge?: BadgeProps
    /** Takes the place of `content` when the value is a class, not a figure. */
    contentBadge?: BadgeProps
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
        xxs: {
          base: 'p-2 gap-1',
          title: 'text-xxs! items-center text-grey',
          content: 'font-bold text-base',
          sub: 'text-sm!',
          iconSize: 'xxs'
        },
        xs: {
          base: 'p-2 gap-2',
          title: 'text-xxs! text-grey',
          content: 'text-base!',
          sub: 'text-xxs!',
          iconSize: 'xs'
        },
        sm: {
          base: 'p-3 gap-2',
          title: 'text-xs! text-grey',
          content: 'text-base! mb-1!',
          sub: 'text-xxs!',
          iconSize: 'xs'
        },
        md: {
          base: 'p-4 gap-2',
          title: 'text-sm! items-center',
          content: 'text-[22px]!',
          sub: 'text-sm!',
          iconSize: 'xs'
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
    {#if subContent && size !== 'xxs'}
      <p class={['text-grey mb-0!', classes.sub]}>
        {@html sanitize(subContent)}
      </p>
    {/if}
  </div>
{/snippet}

<svelte:element
  this={rootTag}
  {id}
  class={['cg-border bg-white flex flex-col', classes.base, props.class]}
>
  <div class={['gap-1 flex', { 'items-start': size === 'xs' }]}>
    <svelte:element
      this={titleTag}
      class={['gap-1 font-normal mb-0! p-0! min-w-0 flex', classes.title, titleClass]}
    >
      <Icon {icon} size={classes.iconSize} block class={size !== 'xxs' ? iconClass : undefined} />
      {title}
    </svelte:element>

    {#if size !== 'xxs'}
      <div class="gap-1 ms-auto flex shrink-0 items-center">
        {#if badge}
          <Badge {...badge} size="sm" />
        {/if}
        {#if tooltip}
          <Tooltip
            id="tooltip-{id}"
            size="xs"
            class={['lh-none! block!', { 'text-grey': size !== 'md' }]}
          >
            {@html sanitize(tooltip)}
          </Tooltip>
        {/if}
      </div>
    {/if}
  </div>

  <svelte:element this={contentTag} class="p-0">
    {#if content}
      {@render innerContent(content, subContent)}
    {:else if size === 'xxs' && (badge ?? contentBadge)}
      <!-- The header row is hidden at this size, so the badge is the value. -->
      <Badge
        {...(badge ?? contentBadge)!}
        tooltip={undefined}
        size="xs"
        class="px-1! leading-tight! tracking-normal! max-w-full text-center whitespace-normal!"
      />
    {:else if contentBadge}
      <Badge
        {...contentBadge}
        size={size === 'md' ? 'md' : 'sm'}
        class="leading-tight! max-w-full text-center whitespace-normal!"
      />
    {:else}
      {@render children?.()}
    {/if}
  </svelte:element>

  {#if desc && size === 'md'}
    <p class="bg-very-light-primary text-xxs p-1 mb-0! b-light-primary rounded-sm mt-auto! border">
      {desc}
    </p>
  {/if}
</svelte:element>
