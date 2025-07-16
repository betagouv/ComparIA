<script lang="ts">
  import GuidedCardComponent from '$lib/components/GuidedCard.svelte'
  import { m } from '$lib/i18n/messages'
  import promptsTable from '$lib/promptsTable'
  import { createEventDispatcher } from 'svelte'

  // Interface pour les données des cartes, utilisant des props au lieu de HTML brut
  interface GuidedCardData {
    iconSrc: string
    iconAlt: string
    title: string
    value: string
    isIASummit?: boolean
    iaSummitSmallIconSrc?: string
    iaSummitTooltip?: string
  }

  const totalGuidedCardsChoices: GuidedCardData[] = [
    { value: 'ideas' as const, iconSrc: 'lightbulb-line' },
    { value: 'explanations' as const, iconSrc: 'chat-3-line' },
    { value: 'languages' as const, iconSrc: 'translate-2' },
    { value: 'administrative' as const, iconSrc: 'draft-line' },
    { value: 'recipes' as const, iconSrc: 'bowl' },
    { value: 'coach' as const, iconSrc: 'clipboard-line' },
    { value: 'stories' as const, iconSrc: 'book-open' },
    { value: 'recommendations' as const, iconSrc: 'music-2-line' }
  ].map((item) => ({
    ...item,
    title: m[`arenaHome.suggestions.choices.${item.value}.title`](),
    iconAlt: m[`arenaHome.suggestions.choices.${item.value}.iconAlt`]()
  }))

  const iaSummitChoice: GuidedCardData = {
    value: 'iasummit',
    iconSrc: '/iasummit.png', // Updated to use imported variable
    iconAlt: m['arenaHome.suggestions.choices.iasummit.iconAlt'](),
    title: m['arenaHome.suggestions.choices.iasummit.title'](),
    isIASummit: true,
    iaSummitSmallIconSrc: '/iasummit-small.png', // Updated to use imported variable
    iaSummitTooltip: m['arenaHome.suggestions.choices.iasummit.tooltip']()
  }

  let displayedCards: GuidedCardData[] = []
  const dispatch = createEventDispatcher()

  function shuffleArray<T>(array: T[]): T[] {
    const newArray = [...array]
    for (let i = newArray.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
    }
    return newArray
  }

  // Helper function to select a random item from an array
  function selectRandomFromArray<T>(array: T[]): T | undefined {
    if (!array || array.length === 0) {
      return undefined
    }
    return array[Math.floor(Math.random() * array.length)]
  }

  const shuffled = shuffleArray(totalGuidedCardsChoices)
  displayedCards = [iaSummitChoice, ...shuffled.slice(0, 3)]

  let currentSelectedCategoryValue: string | null = null

  // Helper function to dispatch prompt with or without selection
  function dispatchPromptWithSelection(promptText: string, origin: string) {
    let selectionStart: number | undefined = undefined
    let selectionEnd: number | undefined = undefined
    const startIndex = promptText.indexOf('[')
    const endIndex = promptText.indexOf(']')

    if (startIndex !== -1 && endIndex !== -1 && endIndex > startIndex) {
      selectionStart = startIndex // Include the opening bracket
      selectionEnd = endIndex + 1 // Include the closing bracket
    }

    if (selectionStart !== undefined && selectionEnd !== undefined) {
      console.log(
        `[GuidedPromptSuggestions] ${origin}: dispatching promptselected with selection. Text: "${promptText}", Start: ${selectionStart}, End: ${selectionEnd}`
      )
      dispatch('promptselected', { text: promptText, selectionStart, selectionEnd })
    } else {
      console.log(
        `[GuidedPromptSuggestions] ${origin}: dispatching promptselected without selection. Text: "${promptText}"`
      )
      dispatch('promptselected', { text: promptText })
    }
  }

  function shufflePrompts() {
    if (currentSelectedCategoryValue) {
      const promptsForCategory = promptsTable[currentSelectedCategoryValue]
      const randomPromptText = selectRandomFromArray(promptsForCategory)

      if (randomPromptText) {
        dispatchPromptWithSelection(randomPromptText, 'shufflePrompts')
      } else {
        console.warn(
          `[GuidedPromptSuggestions] No prompts found for the current category: ${currentSelectedCategoryValue}.`
        )
      }
    } else {
      console.warn('No category currently selected. Cannot shuffle prompts.')
    }
  }

  function handleCardSelect(event: CustomEvent<{ value: string }>) {
    const categoryValue = event.detail.value
    currentSelectedCategoryValue = categoryValue

    const promptsForCategory = promptsTable[categoryValue]
    const randomPromptText = selectRandomFromArray(promptsForCategory)

    if (randomPromptText) {
      dispatchPromptWithSelection(randomPromptText, 'handleCardSelect')
    } else {
      const fallbackText = `Explorer la catégorie : ${categoryValue}`
      console.warn(
        `[GuidedPromptSuggestions] No prompts found for category: ${categoryValue}. Using fallback: "${fallbackText}"`
      )
      dispatch('promptselected', { text: fallbackText }) // No selection for fallback
    }
  }
</script>

<div class="fr-container fr-px-0">
  <h4 class="text-grey-200 fr-text--md fr-mt-md-5w fr-mt-5v fr-mb-3v fr-pb-0 fr-px-0">
    <strong>{m['arenaHome.suggestions.title']()}</strong>
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
    <div class="text-center">
      <button
        class="fr-btn fr-icon-shuffle fr-btn--icon-left fr-btn--tertiary mobile-w-full fr-mt-2w"
        on:click={shufflePrompts}
      >
        {m['arenaHome.suggestions.generateAnother']()}
      </button>
    </div>
  {/if}
</div>

<style>
  .text-grey-200 {
    color: var(--text-mention-grey); /* Utiliser une variable DSFR si disponible */
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
