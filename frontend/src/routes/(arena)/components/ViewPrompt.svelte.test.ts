import { fireEvent, render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ViewPrompt from './ViewPrompt.svelte'

vi.mock('$lib/models', () => ({
  getModelsContext: () => ({ models: [] })
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

const auth = {
  config: {
    home_title: {} as Record<string, string>,
    home_prompt_placeholder: {} as Record<string, string>
  }
}

vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))

const props = {
  loading: false,
  onPrompt: vi.fn(),
  suggestions: []
}

describe('ViewPrompt', () => {
  beforeEach(() => {
    auth.config.home_title = {}
    auth.config.home_prompt_placeholder = {}
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

  it('sends random mode when manual mode has no model picked', async () => {
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', '[]')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Bonjour' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'random', custom_models_selection: [] })
    )
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

  it('shows the home texts the instance set for the current locale', () => {
    auth.config.home_title = {
      fr: 'Posez votre question, deux IA vous répondent',
      en: 'Ask your question'
    }
    auth.config.home_prompt_placeholder = {
      fr: 'Posez votre question santé ici, sans donnée patient'
    }
    const { getByRole, container } = render(ViewPrompt, props)

    expect(getByRole('heading', { level: 2 }).textContent).toContain(
      'Posez votre question, deux IA vous répondent'
    )
    expect(container.querySelector('#initial-prompt')?.getAttribute('placeholder')).toBe(
      'Posez votre question santé ici, sans donnée patient'
    )
  })

  it('keeps the built-in home texts when the instance set none', () => {
    const { getByRole, container } = render(ViewPrompt, props)

    expect(getByRole('heading', { level: 2 }).textContent).toContain('Comment puis-je vous aider')
    expect(container.querySelector('#initial-prompt')?.getAttribute('placeholder')).toBe(
      'Écrivez votre première requête ici'
    )
  })
})
