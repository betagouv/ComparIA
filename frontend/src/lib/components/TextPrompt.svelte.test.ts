import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import TextPrompt from './TextPrompt.svelte'

/** jsdom has neither a microphone nor a MediaRecorder, so a recording that runs
 * end to end needs both faked. Stopping fires `onstop` the way a browser does. */
function fakeRecorder() {
  const stream = { getTracks: () => [{ stop: vi.fn() }] }
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: async () => stream }
  })
  vi.stubGlobal(
    'MediaRecorder',
    class {
      stream = stream
      onstop: (() => void) | null = null
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(['x']) })
        this.onstop?.()
      }
    }
  )
}

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
        transcribe: async () => ({ text: '', model: '' })
      }
    })

    const mic = getByRole('button', { name: 'Dicter le message' })
    const hint = getByRole('tooltip')
    expect(hint.textContent).toBe('Votre enregistrement est conservé.')
    expect(mic.getAttribute('aria-describedby')).toBe(hint.id)
  })

  it('carries no notice when nothing is kept', () => {
    const { getByRole, queryByRole } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: { maxSeconds: 60, notice: '', transcribe: async () => ({ text: '', model: '' }) }
    })

    expect(queryByRole('tooltip')).toBeNull()
    expect(
      getByRole('button', { name: 'Dicter le message' }).getAttribute('aria-describedby')
    ).toBeNull()
  })

  it('names the model that transcribed, and drops the name with the text', async () => {
    fakeRecorder()
    const { getByRole, getByTestId, queryByText } = render(TextPrompt, {
      id: 'prompt',
      label: 'Prompt',
      value: '',
      voice: {
        maxSeconds: 60,
        notice: '',
        transcribe: async () => ({ text: 'bonjour docteur', model: 'speech/one' })
      }
    })

    const mic = getByRole('button', { name: 'Dicter le message' })
    await fireEvent.click(mic)
    await fireEvent.click(getByRole('button', { name: "Arrêter l'enregistrement" }))

    await waitFor(() => expect(queryByText('Transcrit par one')).not.toBeNull())

    // The name belongs to the text. Clear the box and it has nothing left to
    // name, once it has finished shrinking back into the microphone.
    await fireEvent.input(getByTestId('textbox'), { target: { value: '' } })
    await waitFor(() => expect(queryByText('Transcrit par one')).toBeNull())
  })
})
