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
})
