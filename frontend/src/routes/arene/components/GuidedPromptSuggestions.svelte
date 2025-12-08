<script lang="ts">
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import RadioGroupCard from '$components/RadioGroupCard.svelte'
  import { SUGGESTIONS } from '$lib/generated/suggestions'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { selectRandomFromArray, shuffleArray } from '$lib/utils/commons'

  let {
    onPromptSelected
  }: {
    onPromptSelected: (text: string, selectionStart?: number, selectionEnd?: number) => void
  } = $props()

  const locale = getLocale()
  const suggestionsCategories = $derived.by(() => {
    if (!(locale in SUGGESTIONS)) return []
    let categories = [...SUGGESTIONS[locale as keyof typeof SUGGESTIONS]]
    if (locale === 'fr') {
      const iasummit = categories.splice(
        categories.findIndex((c) => c.icon === 'iasummit'),
        1
      )
      return [iasummit[0], ...shuffleArray(categories)]
    }
    return shuffleArray(categories)
  })
  const suggestionsCategoriesCards = $derived(
    suggestionsCategories.slice(0, 4).map((c) => ({
      ...c,
      label: c.description,
      value: c.title.toLowerCase().replace(/[^a-z]/g, '')
    }))
  )

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
      const categorySuggestions =
        suggestionsCategoriesCards.find((c) => c.value === selected)?.suggestions ?? []
      const randomPromptText = selectRandomFromArray(categorySuggestions)

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
    const promptsForCategory =
      suggestionsCategoriesCards.find((c) => c.value === categoryValue)?.suggestions ?? []
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

{#if suggestionsCategoriesCards.length}
  <div class="fr-container px-0!">
    <h4 class="mb-4! text-dark-grey md:mb-5! md:text-base! text-[14px]!">
      <strong>{m['arenaHome.suggestions.title']()}</strong>
    </h4>

    <RadioGroupCard
      id="guided-cards"
      bind:value={selected}
      options={suggestionsCategoriesCards}
      onChange={handleCardSelect}
    >
      {#snippet item({ value, label, icon, title, tooltip })}
        {#if icon.includes('iasummit')}
          <img
            class="mb-3 md:block hidden dark:invert"
            width="110"
            height="35"
            src="/iasummit.png"
            alt={title}
          />
          <img
            class="me-2 md:hidden inline-block object-contain dark:invert"
            width="24"
            src="/iasummit-small.png"
            alt={title}
          />
        {:else}
          <Icon {icon} aria-label={title} class="me-2 text-primary md:mb-4 md:block" />
        {/if}
        <span>
          {label}
          {#if tooltip}
            <Tooltip id="tooltip-{value}" text={tooltip} />
          {/if}
        </span>
      {/snippet}
    </RadioGroupCard>

    {#if selected}
      <div class="mt-4 md:mt-5 text-center">
        <Button
          icon="shuffle"
          variant="secondary"
          text={m['arenaHome.suggestions.generateAnother']()}
          class="md:w-auto! w-full!"
          onclick={shufflePrompts}
        />
      </div>
    {/if}
  </div>
{/if}

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
