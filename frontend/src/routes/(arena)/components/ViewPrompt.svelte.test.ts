import { fireEvent, render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ViewPrompt from './ViewPrompt.svelte'

const catalog = vi.hoisted(() => ({ models: [] as unknown[] }))

vi.mock('$lib/models', () => ({
  getModelsContext: () => catalog
}))

vi.mock('$lib/chatService.svelte', () => ({
  getModeInfos: () => [
    {
      value: 'random',
      icon: 'i-ri-dice-line',
      title: 'Aléatoire',
      label: 'Aléatoire',
      alt_label: 'Aléatoire',
      description: 'Deux modèles choisis au hasard'
    }
  ]
}))

const props = {
  loading: false,
  onPrompt: vi.fn(),
  suggestions: []
}

describe('ViewPrompt', () => {
  beforeEach(() => {
    catalog.models = []
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear()
    })
  })

  it('shows the submitted prompt and loading status while the first turn is pending', async () => {
    const onPrompt = vi.fn(() => new Promise<void>(() => {}))
    const view = render(ViewPrompt, { ...props, onPrompt })
    const prompt = view.getByRole('textbox')

    await fireEvent.input(prompt, { target: { value: 'Pourquoi le ciel est-il bleu ?' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    expect(onPrompt).toHaveBeenCalledOnce()
    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ prompt_value: 'Pourquoi le ciel est-il bleu ?' })
    )

    await view.rerender({ ...props, onPrompt, loading: true })

    expect(view.getByText('Pourquoi le ciel est-il bleu ?')).toBeInTheDocument()
    expect(view.getByRole('status')).toHaveTextContent('Chargement des réponses')
    expect(view.queryByRole('button', { name: 'Envoyer' })).toBeNull()
  })

  it('restores the populated form when loading stops before initialization', async () => {
    const view = render(ViewPrompt, props)

    await fireEvent.input(view.getByRole('textbox'), {
      target: { value: 'Une question à réessayer' }
    })
    await view.rerender({ ...props, loading: true })
    await view.rerender({ ...props, loading: false, promptError: 'Réessayez' })

    expect(view.getByRole('textbox')).toHaveValue('Une question à réessayer')
    expect(view.getByText('Réessayez')).toBeInTheDocument()
  })

  it('puts the network pause notice in place of the form and keeps the typed prompt', async () => {
    const view = render(ViewPrompt, props)
    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    const pause = {
      detail: 'allowance_spent' as const,
      limit: {
        scope: 'network' as const,
        resets_at: new Date(Date.now() + 3600_000).toISOString(),
        resets_in: 3600,
        llm_ids: []
      }
    }
    await view.rerender({ ...props, pause })

    expect(view.queryByRole('textbox')).toBeNull()
    expect(view.getByText(/pas seulement vous/)).toBeInTheDocument()
    expect(view.getByRole('link', { name: 'Voir le classement' })).toBeInTheDocument()

    await view.rerender({ ...props, pause: undefined })
    expect(view.getByRole('textbox')).toHaveValue('Ma question')
  })

  it('takes a refused pick out of the selection and says why, keeping the prompt', async () => {
    const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0 }
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
    const pickRefusal = {
      detail: 'expensive_allowance_spent' as const,
      limit: {
        scope: 'session' as const,
        resets_at: new Date(Date.now() + 3600_000).toISOString(),
        resets_in: 3600,
        llm_ids: ['expensive-id']
      }
    }
    const onPrompt = vi.fn(async () => {
      await view.rerender({ ...props, onPrompt, pickRefusal })
    })
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    const title = view.getByRole('heading', { name: 'Nous avons retiré GPT-5 de votre sélection' })
    expect(title).toHaveFocus()
    const back = view.getByText(/Il est en pause pour vous et revient à/)
    expect(back.querySelector('time')).toHaveAttribute('datetime', pickRefusal.limit.resets_at)
    await vi.waitFor(() =>
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
    )
    expect(view.getByRole('textbox')).toHaveValue('Ma question')
    expect(view.getByRole('textbox')).not.toHaveAttribute('aria-invalid', 'true')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
  })
})
