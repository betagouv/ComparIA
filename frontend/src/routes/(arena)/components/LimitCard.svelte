<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { focusOnShow } from '$lib/helpers/attachments'
  import type { Snippet } from 'svelte'

  let {
    id,
    icon,
    title,
    text,
    focusTitle = false,
    actions,
    footer
  }: {
    id: string
    icon: string
    title: Snippet
    /** One sentence under the title. */
    text: string
    /** It takes the place of the text box the person just sent from. */
    focusTitle?: boolean
    /** A primary button, then a secondary one. */
    actions: Snippet
    footer?: Snippet
  } = $props()
</script>

<div {id} class="cl-limit-card cg-border px-6 py-8 mx-auto w-full text-center">
  <span class="cl-limit-card__icon mb-4 mx-auto flex items-center justify-center">
    <Icon {icon} size="md" block />
  </span>
  <!-- Shown before anyone sends, it is part of the page and leaves focus alone. -->
  <h3 class="fr-h6 mb-2!" {@attach focusOnShow(() => focusTitle)}>{@render title()}</h3>
  <p class="fr-text--sm mb-6!">{text}</p>

  <div class="gap-3 flex flex-col">
    {@render actions()}
  </div>

  {@render footer?.()}
</div>

<style>
  .cl-limit-card {
    max-width: 26rem;
    background-color: var(--background-default-grey);
  }

  .cl-limit-card__icon {
    width: 2.75rem;
    height: 2.75rem;
    border-radius: 50%;
    background-color: var(--background-action-low-blue-france);
    color: var(--text-action-high-blue-france);
  }
</style>
