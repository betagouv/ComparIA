<script lang="ts">
  import { Icon } from '$components/dsfr'

  let {
    id,
    label,
    description,
    pressed = false,
    onclick
  }: {
    id: string
    label: string
    description?: string | null
    pressed?: boolean
    // Without it the card is a preview: same look, nothing to press.
    onclick?: () => void
  } = $props()

  const descriptionId = $derived(description ? `tool-${id}-description` : undefined)
</script>

{#snippet content()}
  <span class="tool-card__icon h-9 w-9 rounded-lg flex shrink-0 items-center justify-center">
    <Icon icon="i-ri-tools-line" size="sm" />
  </span>
  <span class="min-w-0 flex-1">
    <span class="font-bold block">{label}</span>
    {#if description}
      <span id={descriptionId} class="fr-text--sm mb-0! block text-[--text-mention-grey]">
        {description}
      </span>
    {/if}
  </span>
  <span
    class="tool-card__check h-5 w-5 mt-2 flex shrink-0 items-center justify-center rounded-full"
    aria-hidden="true"
  >
    {#if pressed}
      <Icon icon="i-ri-check-line" size="xs" />
    {/if}
  </span>
{/snippet}

{#if onclick}
  <button
    type="button"
    class="tool-card gap-3 rounded-xl px-4 py-3 flex h-full w-full items-start text-left"
    aria-pressed={pressed}
    aria-describedby={descriptionId}
    {onclick}
  >
    {@render content()}
  </button>
{:else}
  <div
    class="tool-card gap-3 rounded-xl px-4 py-3 flex h-full w-full items-start text-left"
    data-pressed={pressed}
  >
    {@render content()}
  </div>
{/if}

<style>
  .tool-card {
    background-color: var(--background-default-grey);
    border: 1px solid var(--border-default-grey);
    color: var(--text-default-grey);
    transition:
      border-color 120ms ease-out,
      box-shadow 120ms ease-out;
  }

  /* A tap leaves :hover on, so touch screens keep the resting look. */
  @media (hover: hover) {
    button.tool-card:hover {
      background-color: var(--background-default-grey-hover);
      border-color: var(--border-plain-grey);
    }
  }

  @media (hover: none) {
    button.tool-card:hover {
      background-color: var(--background-default-grey);
    }
  }

  .tool-card[aria-pressed='true'],
  .tool-card[data-pressed='true'] {
    border-color: var(--blue-france-main-525);
    box-shadow: inset 0 0 0 1px var(--blue-france-main-525);
  }

  .tool-card[aria-pressed='true'] {
    animation: tool-card-select 160ms ease-out;
  }

  .tool-card__icon {
    background-color: var(--background-contrast-grey);
    color: var(--blue-france-main-525);
  }

  .tool-card[aria-pressed='true'] .tool-card__icon,
  .tool-card[data-pressed='true'] .tool-card__icon {
    background-color: var(--background-action-low-blue-france);
  }

  .tool-card__check {
    border: 1px solid var(--border-default-grey);
  }

  .tool-card[aria-pressed='true'] .tool-card__check,
  .tool-card[data-pressed='true'] .tool-card__check {
    background-color: var(--blue-france-main-525);
    border-color: var(--blue-france-main-525);
    color: var(--text-inverted-blue-france);
  }

  @keyframes tool-card-select {
    from {
      transform: scale(0.98);
    }

    to {
      transform: scale(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .tool-card,
    .tool-card[aria-pressed='true'] {
      transition: none;
      animation: none;
    }
  }
</style>
