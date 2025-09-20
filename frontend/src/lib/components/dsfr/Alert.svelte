<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    title,
    variant = 'info',
    children,
    ...props
  }: {
    title: string
    variant?: 'info' | 'success' | 'warning' | 'error'
  } & SvelteHTMLElements['div'] = $props()
</script>

<div {...props} class={[`cl-alert fr-alert fr-alert--${variant}`, props.class]}>
  <h3 class="fr-alert__title">{title}</h3>
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
