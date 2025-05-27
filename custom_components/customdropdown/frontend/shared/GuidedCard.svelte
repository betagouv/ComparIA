<script lang="ts">
  export let iconSrc: string;
  export let iconAlt: string;
  export let title: string;
  export let value: string;
  export let isIASummit: boolean = false;
  export let iaSummitSmallIconSrc: string | undefined = undefined;
  export let iaSummitTooltip: string | undefined = undefined;

  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  function handleClick() {
    dispatch("select", { value });
  }
</script>

<button
    class="guided-card fr-tile fr-tile--horizontal fr-enlarge-link"
    class:degrade={isIASummit}
    on:click={handleClick}
    aria-label={title}
>
    <div class="fr-tile__body">
        <div class="fr-tile__content">
            {#if isIASummit}
                <div class="mobile-flex degrade-content"> <!-- Renamed class to avoid conflict if .degrade has other styling effects -->
                    <img class="md-visible fr-mb-md-3w fr-mr-1w" width=110 height=35 src={iconSrc} alt={iconAlt} />
                    {#if iaSummitSmallIconSrc}
                        <img class="md-hidden fr-mb-md-3w fr-mr-1w" width=35 height=35 src={iaSummitSmallIconSrc} alt={iconAlt} />
                    {/if}
                    <span class="sommet-description">{@html title}&nbsp; <!-- Use @html for title if it can contain HTML like &nbsp; -->
                        {#if iaSummitTooltip}
                            <a class="fr-icon fr-icon--xs fr-icon--question-line" aria-describedby="sommetia-tooltip-{value}"></a>
                        {/if}
                    </span>
                </div>
                {#if iaSummitTooltip}
                    <span class="fr-tooltip fr-placement" id="sommetia-tooltip-{value}" role="tooltip" aria-hidden="true">{iaSummitTooltip}</span>
                {/if}
            {:else}
                <div class="mobile-flex">
                    <img class="fr-mb-md-2w fr-mr-1w" src={iconSrc} width=20 alt={iconAlt} />
                    <span>{title}</span>
                </div>
            {/if}
        </div>
    </div>
</button>

<style>
    .guided-card {
        width: 100%;
        height: 100%;
        text-align: left;
        display: flex;
        flex-direction: column; /* Ensure content flows as expected */
        justify-content: center; /* Center content vertically */
        padding: 0.75rem; /* fr-p-3v */
        --hover-tint: var(--background-action-low-blue-france-hover);
        --active-tint: var(--background-action-low-blue-france-active);
        font-size: 0.75em;
        border: none; /* Remove default button border */
        background-color: var(--background-default-grey); /* Default background */
        color: var(--text-default-grey); /* Default text color */
    }
    .guided-card:hover {
        background-color: var(--hover-tint);
    }
    .guided-card:active {
        background-color: var(--active-tint);
    }

    .guided-card .fr-tile__body {
      width: 100%;
      display: flex; /* Added to help with alignment */
      align-items: center; /* Align items vertically in the center */
    }

    .guided-card .fr-tile__content {
        width: 100%;
        display: flex;       /* Allow content to flex */
        flex-direction: column; /* Stack elements vertically if needed */
        justify-content: center; /* Center content */
    }

    .mobile-flex {
        display: flex;
        align-items: center;
    }

    .mobile-flex img {
        margin-bottom: 0;
        margin-right: 0.5rem; /* fr-mr-1w */
    }
    
    .degrade-content img.fr-mr-1w { /* Specific for IA Summit card */
        margin-right: 0.5rem; /* fr-mr-1w */
    }


    .sommet-description {
        color: #051f43; /* DSFR Blue France Sun 113 */
        align-self: center;
        font-weight: 500; /* Make it slightly bolder */
    }
    .sommet-description .fr-icon--question-line {
        color: #000091; /* DSFR Blue France Sun 113 - Link color */
    }


    .guided-card span:not(.sommet-description):not(.fr-tooltip) {
        font-weight: 500;
        align-self: center;
    }

    .fr-tooltip {
      font-weight: 400 !important;
      font-size: 0.875rem; /* Ensure tooltip text is readable */
      color: var(--text-inverted-grey); /* Standard tooltip text color */
      background-color: var(--background-contrast-grey); /* Standard tooltip background */
    }

    @media (min-width: 48em) { /* md breakpoint (768px) */
      .guided-card {
        font-size: 0.875em !important;
      }
    }
    .guided-card.degrade {
        background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%);
    }

    /* Styles for md-visible and md-hidden if not defined globally */
    /* These are common utility classes, assuming they might be defined elsewhere by DSFR or Gradio */
    .md-visible {
        display: none !important; /* Important to override other display properties if any */
    }
    .md-hidden {
        display: block !important; /* Or flex, inline-block as per original design */
    }
    @media (min-width: 48em) { /* md breakpoint, DSFR default is 768px */
        .md-visible {
            display: block !important; /* Or inline, flex, etc., as needed */
        }
        .md-hidden {
            display: none !important;
        }
    }
</style>