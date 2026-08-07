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

  it('offers no microphone without a voice input', () => {
    const { queryByRole } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: ''
    })

    expect(queryByRole('button', { name: 'Dicter le message' })).toBeNull()
  })

  it('offers a microphone and the storage notice when given one', () => {
    const { getByRole, getByText } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: {
        maxSeconds: 60,
        notice: 'Votre enregistrement est conservé.',
        transcribe: async () => ''
      }
    })

    expect(getByRole('button', { name: 'Dicter le message' })).toBeTruthy()
    expect(getByText('Votre enregistrement est conservé.')).toBeTruthy()
  })

  it('keeps the storage notice off when nothing is kept', () => {
    const { queryByText } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: { maxSeconds: 60, notice: '', transcribe: async () => '' }
    })

    expect(queryByText(/enregistrement/)).toBeNull()
  })
})
