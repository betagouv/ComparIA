<script lang="ts">
  import Icon from '$lib/components/Icon.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'

  export let iconSrc: string
  export let iconAlt: string
  export let title: string
  export let value: string
  export let isIASummit: boolean = false
  export let iaSummitSmallIconSrc: string | undefined = undefined
  export let iaSummitTooltip: string | undefined = undefined
  export let disabled: boolean = false
  export let selected: boolean = false

  import { createEventDispatcher } from 'svelte'
  const dispatch = createEventDispatcher()

  function handleClick() {
    if (disabled) {
      return
    }
    dispatch('select', { value })
  }
</script>

<button
  class="guided-card"
  class:degrade={isIASummit}
  class:selected
  class:disabled
  on:click={handleClick}
  aria-label={title}
  aria-disabled={disabled}
  aria-pressed={selected}
>
  {#if isIASummit}
    <img
      class="md-visible fr-mb-md-3w fr-mr-1w"
      width="110"
      height="35"
      src={iconSrc}
      alt={iconAlt}
    />
    {#if iaSummitSmallIconSrc}
      <img
        class="md-hidden fr-mb-md-3w fr-mr-1w"
        width="35"
        height="35"
        src={iaSummitSmallIconSrc}
        alt={iconAlt}
      />
    {/if}
    <span class="sommet-description">
      {title}&nbsp;
      {#if iaSummitTooltip}
        <Tooltip id="sommetia-tooltip-{value}" text={iaSummitTooltip} />
      {/if}
    </span>
  {:else}
    <Icon icon={iconSrc} aria-label={iconAlt} class="text-primary me-2 md:mb-4" />
    <span>{title}</span>
  {/if}
</button>

<style>
  .guided-card {
    flex-direction: row;
    padding: 0.75rem; /* fr-p-3v */
    --hover-tint: var(--background-action-low-blue-france-hover);
    --active-tint: var(--background-action-low-blue-france-active);
    font-weight: 500;
    width: 100%;
    height: 100%;
    text-align: left;
    display: flex;
    justify-content: left;
    font-size: 0.75em;
    border: none;
    background-color: var(--background-default-grey);
    color: var(--text-default-grey);

    padding: 1rem;
    align-items: left;
    transition: var(--button-transition);
    cursor: pointer;
    outline: 1px solid #e5e5e5;
    border-radius: 0.5rem;
    background-color: white;
    color: var(--grey-200-850);
    font-weight: 500;
    line-height: var(--line-md);
  }

  .guided-card:hover {
    background-color: var(--hover-tint);
  }

  .guided-card:active {
    background-color: var(--active-tint);
  }

  .guided-card:has(.degrade) {
    background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%);
  }

  @media (min-width: 48em) {
    /* .grid-cols-md-2 {
    grid-template-columns: 1fr 1fr;
  }

  .mobile-block {
    display: flex !important;
  }

  .mobile-flex {
    display: block !important;
  } */

    .guided-card {
      flex-direction: column;
      font-size: 0.875em !important;
    }
  }

  .sommet-description {
    color: #051f43;
    align-self: center;
  }

  @media (min-width: 48em) {
    /* md breakpoint (768px) */
    .guided-card {
      font-size: 0.875em !important;
    }
  }
  .guided-card.degrade {
    background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%);
  }

  .md-visible {
    display: none !important;
  }
  .md-hidden {
    display: block !important;
  }
  @media (min-width: 48em) {
    .md-visible {
      display: block !important;
    }
    .md-hidden {
      display: none !important;
    }
  }

  .guided-card.selected,
  .guided-card:active:not(.disabled) {
    outline-offset: 0 !important;
    outline: 2px solid var(--blue-france-main-525) !important;
  }

  /* label > * + * {
		margin-left: var(--size-2);
	} */

  /* input[type="radio"] {
		display: none;
	       */

  .guided-card.disabled {
    cursor: not-allowed;
    background-color: var(--background-disabled-grey);
    color: var(--text-disabled-grey);
    pointer-events: none; /* Empêche les événements de clic */
  }

  .guided-card.disabled:hover,
  .guided-card.disabled:active {
    background-color: var(--background-disabled-grey); /* Conserve la couleur de fond désactivée */
    outline: 1px solid #e5e5e5; /* Conserve le contour par défaut */
  }

  img {
    height: fit-content;
  }
</style>
