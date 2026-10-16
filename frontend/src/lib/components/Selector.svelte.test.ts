import { expectNoA11yViolations, expectNoDanglingAriaRefs } from '$lib/testing/a11y'
import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Selector from './Selector.svelte'

const choices = [
  { value: 'gemma', label: 'Gemma 4' },
  {
    value: 'gpt',
    label: 'GPT-5',
    disabledReason: 'Vous avez utilisé votre part de ce modèle. Il revient à 15 h 40.'
  }
]

describe('Selector', () => {
  it('keeps a paused choice in the tab order, read like the others until tried', async () => {
    const view = render(Selector, {
      id: 'models',
      kind: 'checkbox',
      multiple: true,
      label: 'Modèles',
      value: [],
      choices
    })
    const paused = view.getByRole('checkbox', { name: 'GPT-5' })
    // Not `disabled`, which would take it out of the tab order.
    expect(paused).toBeEnabled()
    expect(paused.tabIndex).toBe(0)
    expect(paused).not.toHaveAttribute('aria-disabled')
    expect(paused).not.toHaveAccessibleDescription()
    expect(view.container).not.toHaveTextContent('Il revient')
    expectNoDanglingAriaRefs(view.container)
    await expectNoA11yViolations(view.container)
  })

  // Space on a checkbox is a click, which jsdom does not make from a key.
  it('does not tick a paused choice, and speaks the reason instead', async () => {
    const onChange = vi.fn()
    const view = render(Selector, {
      id: 'models',
      kind: 'checkbox',
      multiple: true,
      value: [],
      choices,
      onChange
    })
    const paused = view.getByRole('checkbox', { name: 'GPT-5' })

    await fireEvent.click(paused)

    expect(paused).not.toBeChecked()
    expect(onChange).not.toHaveBeenCalled()
    await vi.waitFor(() =>
      expect(view.getByRole('status')).toHaveTextContent('Il revient à 15 h 40.')
    )

    await fireEvent.click(view.getByRole('checkbox', { name: 'Gemma 4' }))
    expect(onChange).toHaveBeenCalledWith(['gemma'])
  })

  it('shows the reason in the card it was tried on, until another choice is picked', async () => {
    const view = render(Selector, {
      id: 'models',
      kind: 'checkbox',
      multiple: true,
      value: [],
      choices
    })
    const paused = view.getByRole('checkbox', { name: 'GPT-5' })

    await fireEvent.click(paused)
    expect(paused.closest('label')).toHaveTextContent('Il revient à 15 h 40.')

    await fireEvent.click(view.getByRole('checkbox', { name: 'Gemma 4' }))
    expect(paused.closest('label')).not.toHaveTextContent('Il revient')
  })

  it('does not pick a paused radio either', async () => {
    const onChange = vi.fn()
    const view = render(Selector, { id: 'modes', kind: 'radio', value: 'gemma', choices, onChange })

    await fireEvent.click(view.getByRole('radio', { name: 'GPT-5' }))

    // jsdom does not tick the previous radio back, a browser does.
    expect(view.getByRole('radio', { name: 'GPT-5' })).not.toBeChecked()
    expect(onChange).not.toHaveBeenCalled()
  })
})
