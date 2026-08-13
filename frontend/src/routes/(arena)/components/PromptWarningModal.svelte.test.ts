import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import PromptWarningModal from './PromptWarningModal.svelte'

describe('PromptWarningModal', () => {
  const warnings = ['Votre message semble contenir des données personnelles.']
  const proceedLabel = 'Envoyer quand même'
  const editLabel = 'Modifier mon message'

  it('shows the backend message and both choices', () => {
    const { getByText, getByRole } = render(PromptWarningModal, { warnings })

    expect(getByText(warnings[0])).toBeTruthy()
    expect(getByRole('button', { name: proceedLabel, hidden: true })).toBeTruthy()
    expect(getByRole('button', { name: editLabel, hidden: true })).toBeTruthy()
  })

  it('sends anyway or goes back to edit', async () => {
    const onProceed = vi.fn()
    const onEdit = vi.fn()
    const { getByRole } = render(PromptWarningModal, { warnings, onProceed, onEdit })

    await fireEvent.click(getByRole('button', { name: proceedLabel, hidden: true }))
    expect(onProceed).toHaveBeenCalledOnce()
    expect(onEdit).not.toHaveBeenCalled()

    await fireEvent.click(getByRole('button', { name: editLabel, hidden: true }))
    expect(onEdit).toHaveBeenCalledOnce()
  })

  it('stays closed until a warning arrives', () => {
    const { container, rerender } = render(PromptWarningModal, {})
    const trigger = container.querySelector('[aria-controls="fr-modal-prompt-warning"]')

    expect(trigger?.getAttribute('data-fr-opened')).toBe('false')

    rerender({ warnings })
    expect(trigger?.getAttribute('data-fr-opened')).toBe('true')
  })
})
