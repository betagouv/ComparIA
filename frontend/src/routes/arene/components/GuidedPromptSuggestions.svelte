<script lang="ts">
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import RadioGroupCard from '$components/RadioGroupCard.svelte'
  import { m } from '$lib/i18n/messages'
  import promptsTable from '$lib/promptsTable'
  import { selectRandomFromArray, shuffleArray } from '$lib/utils/commons'
  import type { ClassValue } from 'svelte/elements'

  let {
    onPromptSelected
  }: {
    onPromptSelected: (text: string, selectionStart?: number, selectionEnd?: number) => void
  } = $props()

  // Interface pour les données des cartes, utilisant des props au lieu de HTML brut
  interface GuidedCardData {
    iconSrc: string
    iconAlt: string
    label: string
    value: string
    isIASummit?: boolean
    iaSummitSmallIconSrc?: string
    iaSummitTooltip?: string
    class?: ClassValue
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
    label: m[`arenaHome.suggestions.choices.${item.value}.title`](),
    iconAlt: m[`arenaHome.suggestions.choices.${item.value}.iconAlt`]()
  }))

  const iaSummitChoice: GuidedCardData = {
    value: 'iasummit',
    iconSrc: '/iasummit.png',
    iconAlt: m['arenaHome.suggestions.choices.iasummit.iconAlt'](),
    label: m['arenaHome.suggestions.choices.iasummit.title'](),
    isIASummit: true,
    iaSummitSmallIconSrc: '/iasummit-small.png',
    iaSummitTooltip: m['arenaHome.suggestions.choices.iasummit.tooltip'](),
    class: 'iasummit'
  }

  const displayedCards = [iaSummitChoice, ...shuffleArray(totalGuidedCardsChoices).slice(0, 3)]
  let selected = $state<string>()

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
      onPromptSelected(promptText, selectionStart, selectionEnd)
    } else {
      console.log(
        `[GuidedPromptSuggestions] ${origin}: dispatching promptselected without selection. Text: "${promptText}"`
      )
      onPromptSelected(promptText)
    }
  }

  function shufflePrompts() {
    if (selected) {
      const promptsForCategory = promptsTable[selected]
      const randomPromptText = selectRandomFromArray(promptsForCategory)

      if (randomPromptText) {
        dispatchPromptWithSelection(randomPromptText, 'shufflePrompts')
      } else {
        console.warn(
          `[GuidedPromptSuggestions] No prompts found for the current category: ${selected}.`
        )
      }
    } else {
      console.warn('No category currently selected. Cannot shuffle prompts.')
    }
  }

  function handleCardSelect(categoryValue: string) {
    const promptsForCategory = promptsTable[categoryValue]
    const randomPromptText = selectRandomFromArray(promptsForCategory)

    if (randomPromptText) {
      dispatchPromptWithSelection(randomPromptText, 'handleCardSelect')
    } else {
      const fallbackText = `Explorer la catégorie : ${categoryValue}`
      console.warn(
        `[GuidedPromptSuggestions] No prompts found for category: ${categoryValue}. Using fallback: "${fallbackText}"`
      )
      onPromptSelected(fallbackText) // No selection for fallback
    }
  }
</script>

<div class="fr-container px-0!">
  <h4 class="text-dark-grey text-[14px]! md:text-base! mb-4! md:mb-5!">
    <strong>{m['arenaHome.suggestions.title']()}</strong>
  </h4>

  <RadioGroupCard
    id="guided-cards"
    bind:value={selected}
    options={displayedCards}
    onChange={handleCardSelect}
  >
    {#snippet item({ value, label, iconSrc, iconAlt, iaSummitSmallIconSrc, iaSummitTooltip })}
      {#if value === 'iasummit'}
        <img
          class="mb-3 hidden md:block dark:invert"
          width="110"
          height="35"
          src={iconSrc}
          alt={iconAlt}
        />
        {#if iaSummitSmallIconSrc}
          <img
            class="me-2 inline-block object-contain md:hidden dark:invert"
            width="24"
            src={iaSummitSmallIconSrc}
            alt={iconAlt}
          />
        {/if}
        <span>
          {label}
          {#if iaSummitTooltip}
            <Tooltip id="iasummit-tooltip-{value}" text={iaSummitTooltip} />
          {/if}
        </span>
      {:else}
        <Icon icon={iconSrc} aria-label={iconAlt} class="text-primary me-2 md:mb-4 md:block" />
        <span>{label}</span>
      {/if}
    {/snippet}
  </RadioGroupCard>

  {#if selected}
    <div class="mt-4 text-center md:mt-5">
      <Button
        icon="shuffle"
        variant="secondary"
        text={m['arenaHome.suggestions.generateAnother']()}
        class="w-full! md:w-auto!"
        onclick={shufflePrompts}
      />
    </div>
  {/if}
</div>

<style lang="postcss">
  :global(.iasummit) {
    /* background: linear-gradient(45deg, #e8e9fe 0%, #f2f5fe 36%, #fff 100%) !important; */
    background: linear-gradient(
      57deg,
      rgba(232, 233, 254, 0.6) 8.29%,
      rgba(242, 245, 254, 0.3) 36.19%,
      #fff 96.89%
    ) !important;

    :root[data-fr-theme='dark'] & {
      background: linear-gradient(
        57deg,
        rgba(58, 58, 63, 0.6) 8.29%,
        rgba(65, 66, 68, 0.3) 36.19%,
        rgb(22, 22, 22) 96.89%
      ) !important;
    }
  }
</style>
