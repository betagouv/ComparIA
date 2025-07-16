<script lang="ts" generics="Block extends boolean = false">
  import type { SvelteHTMLElements } from 'svelte/elements'

  type IconProps = {
    icon: string
    size?: 'xs' | 'sm' | 'md' | 'lg'
    block?: Block
  } & SvelteHTMLElements[Block extends false ? 'span' : 'div']

  let { icon, size = 'md', block = false as Block, ...props }: IconProps = $props()
  const classes = $derived(`fr-icon-${icon} fr-icon--${size} ${props.class ?? ''}`)
  // FIXME check if aria-label else set aria-hidden="true"
</script>

{#if block}
  <div {...props as SvelteHTMLElements['div']} class={classes}></div>
{:else}
  <span {...props as SvelteHTMLElements['span']} class={classes}></span>
{/if}

<style>
  /* set icon-size on element itself for div to set its size in block mode */
  .fr-icon--xs,
  .fr-icon--xs::before,
  .fr-icon--xs::after {
    /* overridden */
    --icon-size: 1rem;
  }
  .fr-icon--sm,
  .fr-icon--sm::before,
  .fr-icon--sm::after {
    /* overridden */
    --icon-size: 1.25rem;
  }

  .fr-icon--md {
    --icon-size: 1.5rem;
  }

  .fr-icon--lg {
    --icon-size: 2rem;
  }

  div {
    height: var(--icon-size);
    width: var(--icon-size);
  }
  div::before,
  div::after {
    vertical-align: top;
  }
</style>
