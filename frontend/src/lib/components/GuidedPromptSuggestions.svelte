<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import GuidedCardComponent from "./GuidedCard.svelte";
    import promptsTable from "$lib/promptsTable";

    // Import local SVG icons (assuming they are moved to the same 'shared' directory or a subdirectory)
    // User will need to ensure these files are present at these relative paths.
    import lightbulbIcon from "$lib/icons/lightbulb.svg";
    import chat3Icon from "$lib/icons/chat-3.svg";
    import translate2Icon from "$lib/icons/translate-2.svg";
    import draftIcon from "$lib/icons/draft.svg";
    import bowlIcon from "$lib/icons/bowl.svg";
    import clipboardIcon from "$lib/icons/clipboard.svg";
    import bookOpenLineIcon from "$lib/icons/book-open-line.svg";
    import music2Icon from "$lib/icons/music-2.svg";
    import shuffleIcon from "$lib/icons/shuffle.svg";

    // Interface pour les données des cartes, utilisant des props au lieu de HTML brut
    interface GuidedCardData {
        iconSrc: string;
        iconAlt: string;
        title: string;
        value: string;
        isIASummit?: boolean;
        iaSummitSmallIconSrc?: string;
        iaSummitTooltip?: string;
    }

    const totalGuidedCardsChoices: GuidedCardData[] = [
        {
            iconSrc: lightbulbIcon,
            iconAlt: "Idées",
            title: "Générer de nouvelles idées",
            value: "ideas",
        },
        {
            iconSrc: chat3Icon,
            iconAlt: "Explications",
            title: "Expliquer simplement un concept",
            value: "explanations",
        },
        {
            iconSrc: translate2Icon,
            iconAlt: "Traduction",
            title: "M’exprimer dans une autre langue",
            value: "languages",
        },
        {
            iconSrc: draftIcon,
            iconAlt: "Administratif",
            title: "Rédiger un document administratif",
            value: "administrative",
        },
        {
            iconSrc: bowlIcon,
            iconAlt: "Recettes",
            title: "Découvrir une nouvelle recette de cuisine",
            value: "recipes",
        },
        {
            iconSrc: clipboardIcon,
            iconAlt: "Conseils",
            title: "Obtenir des conseils sur l’alimentation et le sport",
            value: "coach",
        },
        {
            iconSrc: bookOpenLineIcon,
            iconAlt: "Histoires",
            title: "Raconter une histoire",
            value: "stories",
        },
        {
            iconSrc: music2Icon,
            iconAlt: "Recommandations",
            title: "Proposer des idées de films, livres, musiques",
            value: "recommendations",
        },
    ];

    const iaSummitChoice: GuidedCardData = {
        iconSrc: '/iasummit.png', // Updated to use imported variable
        iconAlt: "Sommet pour l'action sur l'IA",
        title: "Prompts issus de la consultation citoyenne sur l’IA&nbsp;",
        value: "iasummit",
        isIASummit: true,
        iaSummitSmallIconSrc: '/iasummit-small.png', // Updated to use imported variable
        iaSummitTooltip:
            "Ces questions sont issues de la consultation citoyenne sur l’IA qui a lieu du 16/09/2024 au 08/11/2024. Elle visait à associer largement les citoyens et la société civile au Sommet international pour l’action sur l’IA, en collectant leurs idées pour faire de l’intelligence artificielle une opportunité pour toutes et tous, mais aussi de nous prémunir ensemble contre tout usage inapproprié ou abusif de ces technologies.",
    };

    let displayedCards: GuidedCardData[] = [];
    const dispatch = createEventDispatcher();

    function shuffleArray<T>(array: T[]): T[] {
        const newArray = [...array];
        for (let i = newArray.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
        }
        return newArray;
    }

    // Helper function to select a random item from an array
    function selectRandomFromArray<T>(array: T[]): T | undefined {
        if (!array || array.length === 0) {
            return undefined;
        }
        return array[Math.floor(Math.random() * array.length)];
    }

    const shuffled = shuffleArray(totalGuidedCardsChoices);
    displayedCards = [iaSummitChoice, ...shuffled.slice(0, 3)];

    let currentSelectedCategoryValue: string | null = null;
   
    // Helper function to dispatch prompt with or without selection
    function dispatchPromptWithSelection(promptText: string, origin: string) {
    	let selectionStart: number | undefined = undefined;
    	let selectionEnd: number | undefined = undefined;
    	const startIndex = promptText.indexOf('[');
    	const endIndex = promptText.indexOf(']');
   
    	if (startIndex !== -1 && endIndex !== -1 && endIndex > startIndex) {
    		selectionStart = startIndex; // Include the opening bracket
    		selectionEnd = endIndex + 1; // Include the closing bracket
    	}
   
    	if (selectionStart !== undefined && selectionEnd !== undefined) {
    		console.log(`[GuidedPromptSuggestions] ${origin}: dispatching promptselected with selection. Text: "${promptText}", Start: ${selectionStart}, End: ${selectionEnd}`);
    		dispatch("promptselected", { text: promptText, selectionStart, selectionEnd });
    	} else {
    		console.log(`[GuidedPromptSuggestions] ${origin}: dispatching promptselected without selection. Text: "${promptText}"`);
    		dispatch("promptselected", { text: promptText });
    	}
    }
   
    function shufflePrompts() {
    	if (currentSelectedCategoryValue) {
    		const promptsForCategory = promptsTable[currentSelectedCategoryValue];
    		const randomPromptText = selectRandomFromArray(promptsForCategory);
   
    		if (randomPromptText) {
    			dispatchPromptWithSelection(randomPromptText, "shufflePrompts");
    		} else {
    			console.warn(
    				`[GuidedPromptSuggestions] No prompts found for the current category: ${currentSelectedCategoryValue}.`,
    			);
    		}
    	} else {
    		console.warn(
    			"No category currently selected. Cannot shuffle prompts.",
    		);
    	}
    }
   
    function handleCardSelect(event: CustomEvent<{ value: string }>) {
    	const categoryValue = event.detail.value;
    	currentSelectedCategoryValue = categoryValue;
   
    	const promptsForCategory = promptsTable[categoryValue];
    	const randomPromptText = selectRandomFromArray(promptsForCategory);
   
    	if (randomPromptText) {
    		dispatchPromptWithSelection(randomPromptText, "handleCardSelect");
    	} else {
    		const fallbackText = `Explorer la catégorie : ${categoryValue}`;
    		console.warn(
    			`[GuidedPromptSuggestions] No prompts found for category: ${categoryValue}. Using fallback: "${fallbackText}"`,
    		);
    		dispatch("promptselected", { text: fallbackText }); // No selection for fallback
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
                <GuidedCardComponent
                    selected={currentSelectedCategoryValue == card.value}
                    iconSrc={card.iconSrc}
                    iconAlt={card.iconAlt}
                    title={card.title}
                    value={card.value}
                    isIASummit={card.isIASummit}
                    iaSummitSmallIconSrc={card.iaSummitSmallIconSrc}
                    iaSummitTooltip={card.iaSummitTooltip}
                    on:select={handleCardSelect}
                />
            </div>
        {/each}
    </div>

    {#if currentSelectedCategoryValue}
        <div class="text-center"><button
            class="fr-btn fr-btn--tertiary mobile-w-full fr-mt-2w"
            on:click={shufflePrompts}
        >
            <!-- <svelte:component this={shuffleIcon} /> -->
            <img class="fr-mr-1v" src={shuffleIcon} alt="Regénérer" title="Générer un autre message" /> Générer un autre message
        </button>
        </div>
    {/if}
</div>

<style>
    /* .icon-shuffle {
  -webkit-mask-image: url("../assets/extra-icons/shuffle.svg");
  mask-image: url("../assets/extra-icons/shuffle.svg");

  mask-size: 16px 16px;
  mask-position: 0 50%;
  mask-repeat: no-repeat;

} */

    .text-grey-200 {
        color: var(
            --text-mention-grey
        ); /* Utiliser une variable DSFR si disponible */
    }

    /* .mobile-flex {
        display: flex;
        align-items: center;
    }

    .mobile-flex img {
        margin-bottom: 0; 
    } */

    /* .grid {
		display: grid;
		grid-template-columns: repeat(var(--min-columns), 1fr);
		gap: 0.625rem; 
		padding: 0.75rem; 
		margin: 0.75rem; 
	}
	@media (min-width: 48em) {
		.grid {
			gap: 1.5rem; 
			grid-template-columns: repeat(var(--columns), 1fr);
		}
	} */

</style>
