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

  it('carries the storage notice on the microphone itself', () => {
    const { getByRole } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: {
        maxSeconds: 60,
        notice: 'Votre enregistrement est conservé.',
        transcribe: async () => ''
      }
    })

    const mic = getByRole('button', { name: 'Dicter le message' })
    expect(mic.getAttribute('title')).toBe('Votre enregistrement est conservé.')
  })

  it('carries no notice when nothing is kept', () => {
    const { getByRole } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: { maxSeconds: 60, notice: '', transcribe: async () => '' }
    })

    expect(getByRole('button', { name: 'Dicter le message' }).getAttribute('title')).toBeNull()
  })
})
