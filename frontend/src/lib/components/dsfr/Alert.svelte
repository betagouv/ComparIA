<script lang="ts">
  import { onMount, type Snippet } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    title,
    variant = 'info',
    small = false,
    focusTitle = false,
    children,
    ...props
  }: {
    /** Text, or a snippet when the title holds markup such as a `<time>`. */
    title: string | Snippet
    variant?: 'info' | 'success' | 'warning' | 'error'
    /** DSFR's small alert: a one-line message rather than a titled block. */
    small?: boolean
    /** Move focus to the title of a full alert once it shows. */
    focusTitle?: boolean
  } & Omit<SvelteHTMLElements['div'], 'title'> = $props()

  let titleEl = $state<HTMLHeadingElement>()

  // From script, so that only a title meant to take focus can.
  onMount(() => {
    if (!focusTitle || !titleEl) return
    titleEl.tabIndex = -1
    titleEl.focus()
  })
</script>

{#snippet titleText()}
  {#if typeof title === 'string'}{title}{:else}{@render title()}{/if}
{/snippet}

<div
  {...props}
  class={[`cl-alert fr-alert fr-alert--${variant}`, { 'fr-alert--sm': small }, props.class]}
>
  {#if small}
    <p>{@render titleText()}</p>
  {:else}
    <h3 class="fr-alert__title" bind:this={titleEl}>{@render titleText()}</h3>
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
