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
                <div class="mobile-flex degrade-content">
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
                    <span class="sommet-description"
                        >{@html title}&nbsp;
                        {#if iaSummitTooltip}
                            <span
                                class="fr-icon fr-icon--xs fr-icon--question-line"
                                aria-describedby="sommetia-tooltip-{value}"
                            ></span>
                        {/if}
                    </span>
                </div>
                {#if iaSummitTooltip}
                    <span
                        class="fr-tooltip fr-placement"
                        id="sommetia-tooltip-{value}"
                        role="tooltip"
                        aria-hidden="true">{iaSummitTooltip}</span
                    >
                {/if}
            {:else}
                <div class="mobile-flex">
                    <img
                        class="fr-mb-md-2w fr-mr-1w"
                        src={iconSrc}
                        width="20"
                        alt={iconAlt}
                    />
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
        flex-direction: column;
        justify-content: center;
        padding: 0.75rem; /* fr-p-3v */
        --hover-tint: var(--background-action-low-blue-france-hover);
        --active-tint: var(--background-action-low-blue-france-active);
        font-size: 0.75em;
        border: none;
        background-color: var(--background-default-grey);
        color: var(--text-default-grey);
    }
    .guided-card:hover {
        background-color: var(--hover-tint);
    }
    .guided-card:active {
        background-color: var(--active-tint);
    }

    .guided-card .fr-tile__body {
        width: 100%;
        display: flex;
        align-items: center;
    }

    .guided-card .fr-tile__content {
        width: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .mobile-flex {
        display: flex;
        align-items: center;
    }

    .mobile-flex img {
        margin-bottom: 0;
        margin-right: 0.5rem; /* fr-mr-1w */
    }

    .degrade-content img.fr-mr-1w {
        margin-right: 0.5rem; /* fr-mr-1w */
    }

    .guided-card:has(.degrade) {
        background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%);
    }

    .guided-card .fr-tooltip {
        font-weight: 400 !important;
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
            font-size: 0.875em !important;
        }
    }

    .sommet-description {
        color: #051f43;
        align-self: center;
        font-weight: 500;
    }
    .sommet-description .fr-icon--question-line {
        color: #000091;
    }

    .guided-card span:not(.sommet-description):not(.fr-tooltip) {
        font-weight: 500;
        align-self: center;
    }

    .guided-card .fr-tooltip {
        font-weight: 400 !important;
        font-size: 0.875rem;
        color: var(--text-inverted-grey);
        background-color: var(--background-contrast-grey);
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
</style>
