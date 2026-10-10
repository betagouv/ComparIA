import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import TextPrompt from './TextPrompt.svelte'

describe('TextPrompt', () => {
  it('reports blocked keyboard and button submission attempts', async () => {
    const onSubmit = vi.fn()
    const onSubmitBlocked = vi.fn()
    const { getByRole, getByTestId } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: 'Continue',
      submitBtn: true,
      submitDisabled: true,
      onSubmit,
      onSubmitBlocked
    })

    await fireEvent.keyDown(getByTestId('textbox'), { key: 'Enter' })
    await fireEvent.click(getByRole('button', { name: 'Envoyer' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(onSubmitBlocked).toHaveBeenCalledTimes(2)
  })

  it('turns the send button into stop while a turn generates', async () => {
    const onSubmit = vi.fn()
    const onSubmitBlocked = vi.fn()
    const onStop = vi.fn()
    const { getByRole, getByTestId, queryByRole, rerender } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: 'Continue',
      submitBtn: true,
      submitDisabled: true,
      stoppable: true,
      onSubmit,
      onSubmitBlocked,
      onStop
    })

    const stop = getByRole('button', { name: 'Arrêter la génération' })
    expect(queryByRole('button', { name: 'Envoyer' })).toBeNull()
    expect(stop.classList.contains('fr-icon-stop-circle-line')).toBe(true)

    // Enter is neither a send nor a stop while generating.
    await fireEvent.keyDown(getByTestId('textbox'), { key: 'Enter' })
    expect(onSubmitBlocked).not.toHaveBeenCalled()

    await fireEvent.click(stop)
    expect(onStop).toHaveBeenCalledOnce()
    expect(onSubmit).not.toHaveBeenCalled()

    // Same element before and after, so focus survives the switch back.
    stop.focus()
    await rerender({
      id: 'prompt',
      label: 'Prompt',
      value: 'Continue',
      submitBtn: true,
      submitDisabled: false,
      stoppable: false,
      onSubmit,
      onStop
    })
    const send = getByRole('button', { name: 'Envoyer' })
    expect(send).toBe(stop)
    expect(document.activeElement).toBe(send)
    expect(send.classList.contains('fr-icon-arrow-up-line')).toBe(true)
  })

  it('holds the stop button while the request is on its way', async () => {
    const onStop = vi.fn()
    const { getByRole } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      submitBtn: true,
      stoppable: true,
      stopping: true,
      onStop
    })

    const stop = getByRole('button', { name: 'Arrêter la génération' })
    expect(stop.getAttribute('aria-disabled')).toBe('true')
    await fireEvent.click(stop)
    expect(onStop).not.toHaveBeenCalled()
  })
})
