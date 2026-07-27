<script lang="ts">
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import RadioGroupCard from '$components/RadioGroupCard.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import {
    getPromptSelection,
    toSuggestionCategoryCards,
    type SuggestionCategory
  } from '$lib/suggestions'
  import { selectRandomFromArray } from '$lib/utils/commons'

  let {
    onPromptSelected,
    suggestions
  }: {
    onPromptSelected: (text: string, selectionStart?: number, selectionEnd?: number) => void
    suggestions: SuggestionCategory[]
  } = $props()

  const locale = getLocale()
  const suggestionsCategoriesCards = $derived(toSuggestionCategoryCards(suggestions, locale))

  let selected = $state<string>()

  // Helper function to dispatch prompt with or without selection
  function dispatchPromptWithSelection(promptText: string, origin: string) {
    const selection = getPromptSelection(promptText)

    if (selection) {
      const [selectionStart, selectionEnd] = selection
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
      const randomPrompt = selectRandomFromArray(categorySuggestions)

      if (randomPrompt) {
        dispatchPromptWithSelection(randomPrompt.text, 'shufflePrompts')
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
    const randomPrompt = selectRandomFromArray(promptsForCategory)

    if (randomPrompt) {
      dispatchPromptWithSelection(randomPrompt.text, 'handleCardSelect')
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
          <Icon {icon} aria-label={title} block class="text-primary me-2 md:mb-4 md:block" />
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
