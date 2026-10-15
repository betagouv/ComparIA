<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    title,
    variant = 'info',
    small = false,
    children,
    ...props
  }: {
    title: string
    variant?: 'info' | 'success' | 'warning' | 'error'
    /** DSFR's small alert: a one-line message rather than a titled block. */
    small?: boolean
  } & SvelteHTMLElements['div'] = $props()
</script>

<div
  {...props}
  class={[`cl-alert fr-alert fr-alert--${variant}`, { 'fr-alert--sm': small }, props.class]}
>
  {#if small}
    <p>{title}</p>
  {:else}
    <h3 class="fr-alert__title">{title}</h3>
  {/if}
  {@render children?.()}
</div>

<style>
  .cl-alert.fr-alert--info {
    --border-plain-info: var(--blue-france-main-525);
    background-color: var(--grey-975-100);
    background-size:
      100% 0px,
      0px 100%,
      100% 0px,
      2.5rem 100%;
  }
</style>
