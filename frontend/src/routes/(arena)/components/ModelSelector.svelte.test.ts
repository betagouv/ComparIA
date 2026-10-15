import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ModelSelector from './ModelSelector.svelte'

const toast = vi.hoisted(() => vi.fn())
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: toast }))

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

  it('falls back to random mode when the modal closes with no model picked', async () => {
    const view = render(ModelSelector, { models: [], mode: 'custom', modelsSelection: [] })

    await fireEvent(
      view.container.ownerDocument.getElementById('modal-mode-selection')!,
      new Event('dsfr.conceal')
    )

    expect(view.getByRole('radio', { name: /Aléatoire/, hidden: true })).toBeChecked()
    expect(toast).toHaveBeenCalledWith(
      'Aucun modèle choisi : la comparaison se fera entre deux modèles aléatoires.',
      5000
    )
  })

  it('keeps manual mode when the modal closes with a model picked', async () => {
    const view = render(ModelSelector, { models: [], mode: 'custom', modelsSelection: ['a'] })

    await fireEvent(
      view.container.ownerDocument.getElementById('modal-mode-selection')!,
      new Event('dsfr.conceal')
    )

    expect(view.getByRole('radio', { name: /Sélection manuelle/, hidden: true })).toBeChecked()
    expect(toast).not.toHaveBeenCalled()
  })
})
