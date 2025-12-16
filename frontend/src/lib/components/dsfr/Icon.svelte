<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'

  type IconProps = {
    icon: string
    size?: 'xxs' | 'xs' | 'sm' | 'md' | 'lg'
    block?: boolean
  } & SvelteHTMLElements['span']

  let { icon, size = 'md', block = false, ...props }: IconProps = $props()

  const classes = $derived([
    `${icon.startsWith('i-') ? '' : 'fr-icon-'}${icon} fr-icon--${size}`,
    { block: block },
    props.class
  ])
  // FIXME check if aria-label else set aria-hidden="true"
</script>

<span {...props} class={classes}></span>

<style>
  /* set icon-size on element itself for div to set its size in block mode */
  .fr-icon--xxs,
  .fr-icon--xxs::before,
  .fr-icon--xxs::after {
    /* overridden */
    --icon-size: 0.75rem;
  }
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

  .block {
    height: var(--icon-size);
    width: var(--icon-size);
  }
  .block,
  .block {
    vertical-align: top;
  }
</style>
