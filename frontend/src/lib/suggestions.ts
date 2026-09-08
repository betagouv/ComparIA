import { shuffleArray } from '$lib/utils/commons'

export type PromptSuggestion = {
  id: string
  text: string
}

export type SuggestionCategory = {
  id: string
  key: string
  title: string
  description: string
  icon: string
  tooltip?: string | null
  suggestions: PromptSuggestion[]
}

export type PublicSuggestions = {
  categories: SuggestionCategory[]
}

export type SuggestionCategoryCard = SuggestionCategory & {
  label: string
  value: string
}

/**
 * Returns a fresh, shuffled selection of categories for the arena. The summit
 * category keeps its existing first position in French, while every other
 * category remains randomised.
 */
export function getGuidedSuggestionCategories(
  categories: SuggestionCategory[],
  locale: string
): SuggestionCategory[] {
  const activeCategories = categories.filter((category) => category.suggestions.length > 0)

  if (locale !== 'fr') return shuffleArray(activeCategories)

  const summitIndex = activeCategories.findIndex((category) => category.icon === 'iasummit')
  if (summitIndex === -1) return shuffleArray(activeCategories)

  const summitCategory = activeCategories[summitIndex]
  const remainingCategories = activeCategories.filter((_, index) => index !== summitIndex)
  return [summitCategory, ...shuffleArray(remainingCategories)]
}

export function toSuggestionCategoryCards(
  categories: SuggestionCategory[],
  locale: string
): SuggestionCategoryCard[] {
  return getGuidedSuggestionCategories(categories, locale)
    .slice(0, 4)
    .map((category) => ({
      ...category,
      label: category.description,
      value: category.key
    }))
}

export function getPromptSelection(promptText: string): [number, number] | undefined {
  const selectionStart = promptText.indexOf('[')
  const selectionEnd = promptText.indexOf(']')

  if (selectionStart === -1 || selectionEnd <= selectionStart) return undefined

  return [selectionStart, selectionEnd + 1]
}
