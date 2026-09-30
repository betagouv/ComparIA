import { describe, expect, it } from 'vitest'
import {
  getGuidedSuggestionCategories,
  getPromptSelection,
  toSuggestionCategoryCards,
  type SuggestionCategory
} from './suggestions'

const category = (overrides: Partial<SuggestionCategory> = {}): SuggestionCategory => ({
  id: crypto.randomUUID(),
  key: 'administrative',
  title: 'Administrative',
  description: 'Write an administrative document',
  icon: 'i-ri-draft-line',
  suggestions: [{ id: crypto.randomUUID(), text: 'Write to [a public service]' }],
  ...overrides
})

describe('guided suggestions', () => {
  it('keeps the French summit category first without changing API data', () => {
    const summit = category({ key: 'summit', icon: 'iasummit' })
    const categories = [category({ key: 'one' }), summit, category({ key: 'two' })]
    const originalKeys = categories.map((item) => item.key)

    const guidedCategories = getGuidedSuggestionCategories(categories, 'fr')

    expect(guidedCategories[0]).toBe(summit)
    expect(guidedCategories).toHaveLength(3)
    expect(categories.map((item) => item.key)).toEqual(originalKeys)
  })

  it('does not manufacture a summit category when it is absent', () => {
    const categories = [category({ key: 'one' }), category({ key: 'two' })]

    expect(getGuidedSuggestionCategories(categories, 'fr')).toHaveLength(2)
  })

  it('exposes at most four selectable categories with stable API keys', () => {
    const categories = [
      category({ key: 'empty', suggestions: [] }),
      ...Array.from({ length: 5 }, (_, index) => category({ key: `category-${index}` }))
    ]

    const cards = toSuggestionCategoryCards(categories, 'da')

    expect(cards).toHaveLength(4)
    expect(cards.every((card) => card.value.startsWith('category-'))).toBe(true)
  })

  it('identifies the editable bracketed portion of a prompt', () => {
    expect(getPromptSelection('Write to [a public service]')).toEqual([9, 27])
    expect(getPromptSelection('No editable text')).toBeUndefined()
    expect(getPromptSelection('Unclosed [placeholder')).toBeUndefined()
  })
})
