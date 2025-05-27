<script lang="ts">
	import { createEventDispatcher, onMount } from "svelte";
	import { Splide, SplideSlide } from "@splidejs/svelte-splide";
	import "@splidejs/svelte-splide/css/core"; // Utilisation du thème core, plus minimaliste. Ou '@splidejs/svelte-splide/css' pour le thème par défaut.

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

	// Table des prompts (version abrégée pour l'exemple)
	// TODO: Compléter cette table avec tous les prompts de config.py
	const promptsTable: { [key: string]: string[] } = {
		"ideas": [
			"Je prépare une session de brainstorming sur [sujet] avec 15 personnes. Propose moi tes 3 meilleures idées pour lancer des discussions créatives.",
			"En tant que rédacteur publicitaire très reconnu dans ton domaine, propose 5 noms pour le nouveau produit [X] qui a pour objectif [Y]. Donne-moi les noms sous forme de tableau et réalise une évaluation pour savoir quel nom fonctionne le mieux en affichant tes critères (score maximum: 5 points)",
		],
		"explanations": [
			"Décris le **processus de fermentation** en utilisant des exemples liés à la cuisine traditionnelle française.",
			"Tu es professeur d'économie. Explique-moi la théorie des jeux de façon simple. Donne-moi des exemples d'application dans le monde réel. À la fin, fournis un glossaire des notions et termes à connaître sur le sujet.",
		],
		"languages": [
			"Peux-tu traduire la phrase suivante en anglais : 'Bonjour, comment allez-vous aujourd'hui ?'",
			"Aide-moi à rédiger un court e-mail en espagnol pour remercier un collègue.",
		],
		"administrative": [
			"Rédige un courrier pour résilier le bail de mon appartement.",
			"Aide-moi à formuler une demande de congé parental.",
		],
		"recipes": [
			"Je voudrais découvrir une recette facile et rapide à base de poulet et de légumes de saison.",
			"Propose une recette gourmande de dessert vegan facile à faire.",
		],
		"coach": [
			"Quels sont les exercices de base pour renforcer le dos ?",
			"Donne-moi des conseils pour une alimentation équilibrée quand on manque de temps.",
		],
		"stories": [
			"Raconte une histoire courte et amusante pour des enfants de 5 ans.",
			"Écris le début d'une nouvelle de science-fiction sur le thème du voyage dans le temps.",
		],
		"recommendations": [
			"Quels films de science-fiction récents me recommanderais-tu ?",
			"Je cherche un bon livre de fantasy à lire, des suggestions ?",
		],
		"iasummit": [
			"Comment l'intelligence artificielle peut-elle contribuer à résoudre les grands défis mondiaux comme le changement climatique ou la santé publique ?",
			"Quelles sont les implications éthiques de l'utilisation de l'IA dans la prise de décision automatisée ?",
			"Comment assurer que les bénéfices de l'IA soient partagés équitablement et ne creusent pas les inégalités existantes ?",
		]
	};


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
		// displayedCards contiendra uniquement les cartes pour le carrousel
		displayedCards = shuffled.slice(0, 4); // Prenons 4 cartes pour le carrousel par exemple
	}

	const splideOptions = {
		perPage: 3,
		arrows: true,
		pagination: false,
		rewind: true, // Permet de revenir au début/fin
		gap: "1rem", // Espace entre les slides, à ajuster
		breakpoints: {
			// Exemples de breakpoints, à ajuster selon les besoins du DSFR
			1024: { // Pour tablettes et petits écrans desktop
				perPage: 2,
			},
			768: { // Pour mobile
				perPage: 1,
			},
		},
	};

	onMount(() => {
		updateDisplayedCards();
	});

	function shufflePrompts() {
		updateDisplayedCards();
	}

	function selectPrompt(categoryValue: string) {
		const promptsForCategory = promptsTable[categoryValue];
		if (promptsForCategory && promptsForCategory.length > 0) {
			const randomPrompt = promptsForCategory[Math.floor(Math.random() * promptsForCategory.length)];
			dispatch("promptselected", { text: randomPrompt });
		} else {
			// Fallback: si aucune catégorie ou aucun prompt n'est trouvé,
			// on pourrait envoyer un texte générique ou la catégorie elle-même.
			// Pour l'instant, on envoie un message de fallback clair.
			const fallbackText = `Explorer la catégorie : ${categoryValue}`;
			console.warn(`No prompts found for category: ${categoryValue}. Using fallback: "${fallbackText}"`);
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
		<!-- Carte iasummit toujours visible et épinglée -->
		<div class="fr-col-12 fr-col-md-6 fr-col-lg-3 fr-mb-2w">
			<button
				class="guided-card fr-tile fr-tile--horizontal fr-enlarge-link"
				on:click={() => selectPrompt(iaSummitChoice.value)}
			>
				<div class="fr-tile__body">
					<div class="fr-tile__content">
						{@html iaSummitChoice.html}
					</div>
				</div>
			</button>
		</div>

		<!-- Carrousel pour les autres cartes -->
		<div class="fr-col-12">
			<Splide options={splideOptions} aria-label="Suggestions de prompts guidés">
				{#each displayedCards as card (card.value)}
					{#if card.value !== "iasummit"}
						<!--
							La div fr-col-12 n'est plus nécessaire ici car SplideSlide gère la largeur du slide.
							Le padding peut être géré par l'option 'gap' de Splide ou des styles sur .guided-card si besoin.
						-->
						<SplideSlide>
							<div class="fr-mb-2w" style="height: 100%; display: flex;"> <!-- Assurer que le bouton prend toute la hauteur -->
								<!-- S'assurer que le bouton prend toute la largeur du slide -->
								<button
									class="guided-card fr-tile fr-tile--horizontal fr-enlarge-link"
									on:click={() => selectPrompt(card.value)}
									style="width: 100%;"
								>
									<div class="fr-tile__body">
										<div class="fr-tile__content">
											{@html card.html}
										</div>
									</div>
								</button>
							</div>
						</SplideSlide>
					{/if}
				{/each}
			</Splide>
		</div>
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
		color: var(--text-mention-grey); /* Utiliser une variable DSFR si disponible */
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
   
 /* Les styles spécifiques à svelte-carousel ont été supprimés. */
 /* Splide a ses propres styles, importés via CSS. */
 /* Vous pouvez ajouter des styles globaux pour surcharger Splide si nécessaire, par exemple : */
 /*
 :global(.splide__arrow) {
  background-color: var(--background-action-low-blue-france) !important;
  opacity: 1 !important;
 }
 :global(.splide__arrow svg) {
  fill: var(--text-action-high-blue-france) !important;
 }
 :global(.splide__slide) {
  padding: 0 0.5rem; // Pour simuler un 'gap' si l'option 'gap' n'est pas suffisante ou pour un contrôle fin
 }
 */

	.mobile-flex {
		display: flex;
		align-items: center;
	}

	.mobile-flex img {
		margin-bottom: 0; /* Annuler la marge pour l'alignement flex */
	}

	/* S'assurer que les icônes DSFR pour les boutons sont bien chargées/stylées */
	.fr-btn.fr-icon-shuffle-line::before {
		-webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000000'%3E%3Cpath d='M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z'%3E%3C/path%3E%3C/svg%3E");
		mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000000'%3E%3Cpath d='M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z'%3E%3C/path%3E%3C/svg%3E");
	}

    /* Styles pour la carte spéciale "Sommet IA" */
    .degrade {
        /* TODO: Recréer le style dégradé si nécessaire, ou utiliser les classes DSFR */
        /* background: linear-gradient(to right, #ff8a00, #e52e71); Exemple */
    }
    .sommet-description {
        /* Styles spécifiques si besoin */
    }
    .fr-tooltip {
        /* Styles DSFR pour le tooltip, s'assurer qu'ils s'appliquent bien */
    }
</style>