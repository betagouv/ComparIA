<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { HTMLAnchorAttributes } from 'svelte/elements'
  import type { ButtonProps } from './Button.svelte'

  type LinkProps = {
    href: string
    text: string
    button?: boolean
    hideExternalIcon?: boolean
  } & ButtonProps &
    HTMLAnchorAttributes

  let {
    href,
    text,
    button = false,
    hideExternalIcon = false,
    size = 'md',
    variant = 'primary',
    icon,
    iconOnly = false,
    iconPos = 'left',
    cornered = false,
    native = !button,
    ...props
  }: LinkProps = $props()

  const externalProps = $derived(
    href.startsWith('http') || href.startsWith('mailto:')
      ? {
          rel: 'noopener external',
          target: '_blank',
          // FIXME a11y mailto
          title: m['a11y.externalLink']({ text })
        }
      : { target: '_self' }
  )

  const btnClasses = $derived([
    `fr-btn fr-btn--${variant}`,
    {
      xs: 'fr-btn--sm px-1! py-0!',
      sm: 'fr-btn--sm',
      md: '',
      lg: 'fr-btn--lg px-6!'
    }[size],
    {
      'cg-link-btn': !native,
      'rounded-lg': !cornered,
      'justify-center': !iconOnly,
      [`fr-icon-${icon}`]: !!icon,
      [`fr-btn--icon-${iconPos}`]: !!icon && !iconOnly,
      'max-w-[1.5rem]! min-h-[1.5rem]! h-[1.5rem]!': size === 'xs' && iconOnly
    }
  ])

  const linkClasses = $derived([
    `fr-link fr-link--${size}`,
    {
      xs: 'fr-link--sm',
      sm: 'fr-link--sm',
      md: '',
      lg: 'fr-link--lg'
    }[size],
    {
      [`fr-icon-${icon} fr-link--icon-${iconPos}`]: !!icon,
      [`text-${variant}!`]: !native
    }
  ])

  const classes = $derived([
    ...(button ? btnClasses : linkClasses),
    { 'after:content-none!': hideExternalIcon },
    props.class ?? ''
  ])
</script>

<a {...externalProps} {...props} {href} class={classes}>
  {text}
</a>

<style lang="postcss">
  /* Override only light theme blue to purple */
  :root[data-fr-theme='light'] .cg-link-btn {
    --background-action-high-blue-france: var(--blue-france-main-525);
    --background-action-high-blue-france-hover: var(--cg-blue-france-main-525-hover);
    --background-action-high-blue-france-active: var(--cg-blue-france-main-525-active);
    --border-action-high-blue-france: var(--blue-france-main-525);
    --text-action-high-blue-france: var(--blue-france-main-525);
  }
  /* To avoid flickering at page load */
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] .cg-link-btn {
      --background-action-high-blue-france: var(--blue-france-main-525);
      --background-action-high-blue-france-hover: var(--cg-blue-france-main-525-hover);
      --background-action-high-blue-france-active: var(--cg-blue-france-main-525-active);
      --border-action-high-blue-france: var(--blue-france-main-525);
      --text-action-high-blue-france: var(--blue-france-main-525);
    }
  }
</style>
