import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import GuidedPromptSuggestions from './GuidedPromptSuggestions.svelte'

const suggestions = [
  {
    id: 'category-id',
    key: 'administrative',
    title: 'Administrative',
    description: 'Write an administrative document',
    icon: 'i-ri-draft-line',
    suggestions: [{ id: 'suggestion-id', text: 'Write to [a public service]' }]
  }
]

describe('GuidedPromptSuggestions', () => {
  it('uses API suggestions and selects the bracketed placeholder when a card is chosen', async () => {
    const onPromptSelected = vi.fn()
    const { getByRole } = render(GuidedPromptSuggestions, { suggestions, onPromptSelected })

    await fireEvent.click(
      getByRole('radio', { name: 'Administrative Write an administrative document' })
    )

    expect(onPromptSelected).toHaveBeenCalledWith('Write to [a public service]', 9, 27)
  })

  it('hides itself when the API has no active suggestions', () => {
    const { queryByRole } = render(GuidedPromptSuggestions, {
      suggestions: [],
      onPromptSelected: vi.fn()
    })

    expect(queryByRole('radio')).toBeNull()
  })
})
