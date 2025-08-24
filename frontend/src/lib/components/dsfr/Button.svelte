<script lang="ts">
  import type { HTMLButtonAttributes } from 'svelte/elements'

  export type ButtonProps = {
    text?: string
    size?: 'xs' | 'sm' | 'md' | 'lg'
    variant?: 'primary' | 'secondary' | 'tertiary' | 'tertiary-no-outline'
    icon?: string
    iconOnly?: boolean
    iconPos?: 'left' | 'right'
    cornered?: boolean
    native?: boolean
  }

  let {
    text,
    size = 'md',
    variant = 'primary',
    icon,
    iconOnly = false,
    iconPos = 'left',
    cornered = false,
    native = false,
    children,
    ...props
  }: Omit<HTMLButtonAttributes, 'size'> & ButtonProps = $props()

  const classes = $derived([
    `fr-btn fr-btn--${variant}`,
    {
      xs: 'fr-btn--sm px-1! py-0!',
      sm: 'fr-btn--sm',
      md: '',
      lg: 'fr-btn--lg px-6!'
    }[size],
    {
      'cg-btn': !native,
      'rounded-lg': !cornered,
      'justify-center': !iconOnly,
      [`fr-icon-${icon}`]: !!icon,
      [`fr-btn--icon-${iconPos}`]: !!icon && !iconOnly,
      'max-w-[1.5rem]! min-h-[1.5rem]! h-[1.5rem]!': size === 'xs' && iconOnly
    },
    props.class ?? ''
  ])
</script>

<button {...props} class={classes}>
  {#if text}{text}{:else}{@render children?.()}{/if}
</button>

<style lang="postcss">
  /* Override only light theme blue to purple */
  :root[data-fr-theme='light'] .cg-btn {
    --background-action-high-blue-france: var(--blue-france-main-525);
    --background-action-high-blue-france-hover: var(--cg-blue-france-main-525-hover);
    --background-action-high-blue-france-active: var(--cg-blue-france-main-525-active);
    --border-action-high-blue-france: var(--blue-france-main-525);
    --text-action-high-blue-france: var(--blue-france-main-525);
  }
  /* To avoid flickering at page load */
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] .cg-btn {
      --background-action-high-blue-france: var(--blue-france-main-525);
      --background-action-high-blue-france-hover: var(--cg-blue-france-main-525-hover);
      --background-action-high-blue-france-active: var(--cg-blue-france-main-525-active);
      --border-action-high-blue-france: var(--blue-france-main-525);
      --text-action-high-blue-france: var(--blue-france-main-525);
    }
  }
</style>
