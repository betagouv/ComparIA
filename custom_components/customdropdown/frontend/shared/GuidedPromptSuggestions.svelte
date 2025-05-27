<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";

    interface GuidedCard {
        html: string;
        value: string;
    }

    const totalGuidedCardsChoices: GuidedCard[] = [
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/lightbulb.svg" width=20 alt="Idées" />
            <span id="ideas-description">Générer de nouvelles idées</span>
        </div>`,
            value: "ideas",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/chat-3.svg" width=19 alt="Explications" />
            <span id="explanations-description">Expliquer simplement un concept</span>
        </div>`,
            value: "explanations",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/translate-2.svg" width=20 alt="Traduction" />
            <span id="languages-description">M’exprimer dans une autre langue</span>
        </div>`,
            value: "languages",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/draft.svg" width=20 alt="Administratif" />
            <span id="administrative-description">Rédiger un document administratif</span>
        </div>`,
            value: "administrative",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/bowl.svg" width=20 alt="Recettes" />
            <span id="recipes-description">Découvrir une nouvelle recette de cuisine</span>
        </div>`,
            value: "recipes",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/clipboard.svg" width=20 alt="Conseils" />
            <span id="coach-description">Obtenir des conseils sur l’alimentation et le sport</span>
        </div>`,
            value: "coach",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/book-open-line.svg" width=20 alt="Histoires" />
            <span id="stories-description">Raconter une histoire</span>
        </div>`,
            value: "stories",
        },
        {
            html: `<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/music-2.svg" width=20 alt="Recommandations" />
            <span id="recommendations-description">Proposer des idées de films, livres, musiques</span>
        </div>`,
            value: "recommendations",
        },
    ];

    const iaSummitChoice: GuidedCard = {
        html: `<div class="mobile-flex degrade">
            <img class="md-visible fr-mb-md-3w fr-mr-1w" width=110 height=35 src="../assets/iasummit.png" alt="Sommet pour l'action sur l'IA" />
            <img class="md-hidden fr-mb-md-3w fr-mr-1w" width=35 height=35 src="../assets/iasummit-small.png" alt="Sommet pour l'action sur l'IA" />
            <span class="sommet-description">Prompts issus de la consultation citoyenne sur l’IA&nbsp; <a class="fr-icon fr-icon--xs fr-icon--question-line" aria-describedby="sommetia"></a>
        </span>
        </div>
        <span class="fr-tooltip fr-placement" id="sommetia" role="tooltip" aria-hidden="true">Ces questions sont issues de la consultation citoyenne sur l’IA qui a lieu du 16/09/2024 au 08/11/2024. Elle visait à associer largement les citoyens et la société civile au Sommet international pour l’action sur l’IA, en collectant leurs idées pour faire de l’intelligence artificielle une opportunité pour toutes et tous, mais aussi de nous prémunir ensemble contre tout usage inapproprié ou abusif de ces technologies.</span>`,
        value: "iasummit",
    };

    let displayedCards: GuidedCard[] = [];
    const dispatch = createEventDispatcher();

    import promptsTable from "./promptsTable";

    function shuffleArray<T>(array: T[]): T[] {
        const newArray = [...array];
        for (let i = newArray.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
        }
        return newArray;
    }

    function updateDisplayedCards() {
        const shuffled = shuffleArray(totalGuidedCardsChoices);
        displayedCards = [iaSummitChoice, ...shuffled.slice(0, 3)];
    }

    onMount(() => {
        updateDisplayedCards();
    });

    function shufflePrompts() {
        updateDisplayedCards();
    }

    function selectPrompt(categoryValue: string) {
        const promptsForCategory = promptsTable[categoryValue];
        if (promptsForCategory && promptsForCategory.length > 0) {
            const randomPrompt =
                promptsForCategory[
                    Math.floor(Math.random() * promptsForCategory.length)
                ];
            dispatch("promptselected", { text: randomPrompt });
        } else {
            // Fallback: si aucune catégorie ou aucun prompt n'est trouvé,
            // on pourrait envoyer un texte générique ou la catégorie elle-même.
            // Pour l'instant, on envoie un message de fallback clair.
            const fallbackText = `Explorer la catégorie : ${categoryValue}`;
            console.warn(
                `No prompts found for category: ${categoryValue}. Using fallback: "${fallbackText}"`,
            );
            dispatch("promptselected", { text: fallbackText });
        }
    }
</script>

<div class="fr-container fr-px-0">
    <h4
        class="text-grey-200 fr-text--md fr-mt-md-5w fr-mt-5v fr-mb-3v fr-pb-0 fr-px-0"
    >
        <strong>Suggestions de prompts</strong>
    </h4>

    <div class="fr-grid-row fr-grid-row--gutters">
        {#each displayedCards as card (card.value)}
            <div class="fr-col-12 fr-col-md-6 fr-col-lg-3 fr-mb-2w">
                <button
                    class="guided-card fr-tile fr-tile--horizontal fr-enlarge-link"
                    on:click={() => selectPrompt(card.value)}
                >
                    <div class="fr-tile__body">
                        <div class="fr-tile__content">
                            {@html card.html}
                        </div>
                    </div>
                </button>
            </div>
        {/each}
    </div>

    <button
        class="fr-btn fr-btn--tertiary fr-icon-shuffle-line fr-btn--icon-left fr-mx-auto mobile-w-full fr-mt-2w"
        on:click={shufflePrompts}
    >
        Générer d'autres suggestions
    </button>
</div>

<style>
    .text-grey-200 {
        color: var(
            --text-mention-grey
        ); /* Utiliser une variable DSFR si disponible */
    }

    .guided-card {
        width: 100%;
        height: 100%; /* Pour que toutes les cartes aient la même hauteur */
        text-align: left;
        display: flex; /* Pour mieux contrôler l'alignement interne si besoin */
        padding: 0.75rem; /* fr-p-3v */
        --hover-tint: var(--background-action-low-blue-france-hover);
        --active-tint: var(--background-action-low-blue-france-active);
    }
    .guided-card .fr-tile__content {
        width: 100%; /* S'assurer que le contenu prend toute la largeur */
    }

    /* .mobile-flex {
        display: flex;
        align-items: center;
    }

    .mobile-flex img {
        margin-bottom: 0; 
    } */

    .sommet-description {
        color: #051f43;
    }

    .guided-card span {
  font-weight: 500;
  align-self: center;
  font-size: 0.75em;
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
    .guided-card:has(.degrade) {
        background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%);
    }

    /* S'assurer que les icônes DSFR pour les boutons sont bien chargées/stylées */
    .fr-btn.fr-icon-shuffle-line::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000000'%3E%3Cpath d='M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z'%3E%3C/path%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000000'%3E%3Cpath d='M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z'%3E%3C/path%3E%3C/svg%3E");
    }

    /* FIXME: .fr-tooltip  */
</style>
