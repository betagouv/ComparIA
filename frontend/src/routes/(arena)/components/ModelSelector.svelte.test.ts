import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ModelSelector from './ModelSelector.svelte'

// jsdom has no Web Animations API, which the picker's fade-in needs.
Element.prototype.animate ??= vi.fn(() => ({
  cancel: vi.fn(),
  finished: Promise.resolve()
})) as unknown as Element['animate']

describe('ModelSelector', () => {
  it('reopens the model picker when manual selection is clicked again', async () => {
    const view = render(ModelSelector, { models: [], mode: 'custom', modelsSelection: [] })
    expect(view.queryByLabelText('Rechercher un modèle')).toBeNull()

    await fireEvent.click(view.getByRole('radio', { name: /Sélection manuelle/, hidden: true }))

    expect(view.getByLabelText('Rechercher un modèle')).toBeInTheDocument()
  })
})
