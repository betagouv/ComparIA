<script lang="ts">
  import type { HTMLButtonAttributes } from 'svelte/elements'

  export type ButtonProps = {
    text?: string
    size?: 'sm' | 'md' | 'lg'
    variant?: 'primary' | 'secondary' | 'tertiary' | 'tertiary-no-outline'
    icon?: string
    iconPos?: 'left' | 'right'
    cornered?: boolean
    native?: boolean
  }

  let {
    text,
    size = 'md',
    variant = 'primary',
    icon,
    iconPos = 'left',
    cornered = false,
    native = false,
    children,
    ...props
  }: Omit<HTMLButtonAttributes, 'size'> & ButtonProps = $props()

  const classes = $derived([
    `fr-btn fr-btn--${variant} justify-center`,
    {
      sm: 'fr-btn--sm',
      md: '',
      lg: 'fr-btn--lg px-6!'
    }[size],
    {
      'cg-btn': !native,
      'rounded-lg': !cornered,
      [`fr-icon-${icon} fr-btn--icon-${iconPos}`]: !!icon
    },
    props.class ?? ''
  ])
</script>

<button {...props} class={classes}>
  {#if text}{text}{:else}{@render children?.()}{/if}
</button>

<style>
  /* Override only light theme blue to purple */
  :root[data-fr-theme='light'] .cg-btn {
    --background-action-high-blue-france: var(--blue-france-main-525);
    --background-action-high-blue-france-hover: var(--cg-blue-france-main-525-hover);
    --background-action-high-blue-france-active: var(--cg-blue-france-main-525-active);
    --border-action-high-blue-france: var(--blue-france-main-525);
    --text-action-high-blue-france: var(--blue-france-main-525);
  }
</style>
