import { api } from '$lib/fastapi-client'
import type { ArenaLimits } from '$lib/generated/backend'
import { createLimits, type Limits } from '$lib/limits.svelte'
import { fireEvent, render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ViewPrompt from './ViewPrompt.svelte'

const catalog = vi.hoisted(() => ({ models: [] as unknown[] }))
const arena = vi.hoisted(() => ({
  limits: undefined as unknown,
  url: new URL('http://localhost/')
}))

vi.mock('$lib/models', () => ({
  getModelsContext: () => catalog
}))
vi.mock('$lib/limits.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/limits.svelte')>()),
  getLimitsContext: () => arena.limits
}))
vi.mock('$app/state', () => ({
  page: {
    get url() {
      return arena.url
    }
  }
}))
vi.mock('$app/navigation', () => ({ goto: vi.fn() }))

vi.mock('$lib/chatService.svelte', () => ({
  getModeInfos: () => [
    {
      value: 'random',
      icon: 'i-ri-dice-line',
      title: 'Aléatoire',
      label: 'Aléatoire',
      alt_label: 'Aléatoire',
      description: 'Deux modèles choisis au hasard'
    },
    {
      value: 'small-models',
      icon: 'i-ri-leaf-line',
      title: 'Frugal',
      label: 'Frugal',
      alt_label: 'Frugal',
      description: 'Deux petits modèles'
    },
    {
      value: 'big-vs-small',
      icon: 'i-ri-ruler-line',
      title: 'David contre Goliath',
      label: 'David contre Goliath',
      alt_label: 'David contre Goliath',
      description: 'Un petit modèle contre un grand'
    }
  ]
}))

const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0, name: 'Lab' }
const badges = {}
// What GET /arena/limits says once the expensive allowance is spent.
function expensiveSpent(...ids: string[]): ArenaLimits {
  return {
    total: null,
    expensive: { scope: 'session', resets_at: null, resets_in: 3600 },
    paused_llms: ids.map((id) => ({ id, until: null, reason: 'allowance' as const }))
  }
}

const props = {
  loading: false,
  onPrompt: vi.fn(),
  suggestions: []
}

describe('ViewPrompt', () => {
  beforeEach(() => {
    catalog.models = []
    arena.limits = createLimits()
    arena.url = new URL('http://localhost/')
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
    expect(view.getByText(/la limite vaut pour tout le réseau/)).toBeInTheDocument()
    expect(view.getByRole('link', { name: 'Voir le classement' })).toHaveAttribute(
      'href',
      '/ranking'
    )
    expect(view.getByRole('link', { name: 'Découvrir les modèles' })).toHaveAttribute(
      'href',
      '/models'
    )
    // Shown before anyone sent from here: part of the page, focus stays.
    expect(view.getByRole('heading', { name: /^De retour à/ })).not.toHaveFocus()

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

    // One line, focused: nothing started, and this says why.
    const title = view.container.querySelector<HTMLElement>('#pick-paused-notice')!
    expect(title).toHaveFocus()
    expect(title).toHaveTextContent(
      /^GPT-5 est en pause pour vous jusqu'à .*, on l'a retiré\. Pourquoi \?$/
    )
    expect(title.querySelector('time')).toHaveAttribute('datetime', pickRefusal.limit.resets_at)
    expect(view.queryByRole('heading', { level: 3 })).toBeNull()
    await vi.waitFor(() =>
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
    )
    expect(view.getByRole('textbox')).toHaveValue('Ma question')
    expect(view.getByRole('textbox')).not.toHaveAttribute('aria-invalid', 'true')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
    // Two models were picked, so one is left and the mode stays custom.
    expect(view.queryByText(/aléatoire/)).toBeNull()
    // The notice sits after the send button, as it shows on screen.
    const send = view.getByRole('button', { name: 'Envoyer' })
    expect(send.compareDocumentPosition(title) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('says a refused pick is full for the day, not paused for the person', async () => {
    const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0 }
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
    const pickRefusal = {
      detail: 'model_full_today' as const,
      limit: {
        scope: null,
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

    const title = view.container.querySelector<HTMLElement>('#pick-paused-notice')!
    expect(title).toHaveFocus()
    expect(title).toHaveTextContent(
      /^Complet aujourd'hui : on a retiré GPT-5 de votre sélection\. Pourquoi \?$/
    )
    expect(title).not.toHaveTextContent(/pour vous/)
    await vi.waitFor(() =>
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
    )
  })

  it('asks to send again shortly when too many messages went at once', async () => {
    const view = render(ViewPrompt, {
      ...props,
      busyHint: 'Trop de messages en même temps, réessayez dans quelques secondes.'
    })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    expect(view.getByText(/réessayez dans quelques secondes/)).toBeInTheDocument()
    // A hint, not an error in what was typed: sending stays open.
    expect(view.getByRole('textbox')).not.toHaveAttribute('aria-invalid', 'true')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
  })

  it('takes a saved pick paused since out of the selection before anyone sends', async () => {
    // Midday, so the hour back never falls after midnight.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 14, 12, 0))
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
    arena.limits = createLimits(expensiveSpent('expensive-id'))

    const view = render(ViewPrompt, props)

    await view.findAllByText(/GPT-5 est en pause/)
    const notice = view.container.querySelector('#pick-paused-notice')!
    expect(notice).toHaveTextContent(
      /^GPT-5 est en pause pour vous jusqu'à 13\sh\s00, on l'a retiré\. Pourquoi \?$/
    )
    // Not focused: nobody sent anything.
    expect(notice).not.toHaveFocus()
    // An hour on from midday, the countdown the server sent.
    expect(notice.querySelector('time')).toHaveAttribute(
      'datetime',
      new Date(2026, 9, 14, 13, 0).toISOString()
    )
    await vi.waitFor(() =>
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
    )
    expect(localStorage.getItem('mode')).toBe('custom')
    // Told to a screen reader too: it may land after the page showed.
    expect(view.getAllByRole('status')[0]).toHaveTextContent(/GPT-5 est en pause pour vous/)
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeInTheDocument()

    // Gone once the person picks for themselves.
    await fireEvent.click(view.getByRole('radio', { name: /Frugal/, hidden: true }))
    expect(view.container.querySelector('#pick-paused-notice')).toBeNull()
    ;(arena.limits as Limits).destroy()
    vi.useRealTimers()
  })

  it('keeps the form out of sight until the limits are read, two seconds at most', async () => {
    vi.useFakeTimers()
    arena.limits = createLimits(null, { pending: true })

    const view = render(ViewPrompt, props)

    const form = view.container.querySelector<HTMLElement>('#prompt-form')!
    // Hidden, so a pause never replaces a text box someone saw; shown again
    // when JavaScript is off, see app.html.
    expect(form).toHaveClass('invisible', 'cl-limits-pending')
    await vi.advanceTimersByTimeAsync(2000)
    expect(form).not.toHaveClass('invisible')
    ;(arena.limits as Limits).destroy()
    vi.useRealTimers()
  })

  it('tells a full model and a paused one taken out of a pick each by its own reason', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 14, 12, 0))
    catalog.models = [
      { id: 'full-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'paused-id', name: 'Kimi K3', status: 'enabled', lab, badges, params: 1000 },
      { id: 'open-a', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
      { id: 'open-b', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['full-id', 'paused-id']))
    const spent = expensiveSpent('paused-id')
    arena.limits = createLimits({
      ...spent,
      paused_llms: [
        ...spent.paused_llms,
        { id: 'full-id', until: '2026-10-14T22:00:00Z', reason: 'full' }
      ]
    })

    const view = render(ViewPrompt, props)

    await view.findAllByText(/Complet aujourd'hui/)
    expect(view.container.querySelector('#pick-paused-notice')).toHaveTextContent(
      /^Complet aujourd'hui : on a retiré GPT-5 de votre sélection\. Kimi K3 est en pause pour vous jusqu'à 13\sh\s00, on l'a retiré, la comparaison sera aléatoire\. Pourquoi \?$/
    )
    ;(arena.limits as Limits).destroy()
    vi.useRealTimers()
  })

  it('says a pick is paused for the network when the network spent the allowance', async () => {
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
    const spent = expensiveSpent('expensive-id')
    arena.limits = createLimits({ ...spent, expensive: { ...spent.expensive!, scope: 'network' } })

    const view = render(ViewPrompt, props)

    await view.findAllByText(/GPT-5 est en pause/)
    expect(view.container.querySelector('#pick-paused-notice')).toHaveTextContent(
      /^GPT-5 est en pause pour votre réseau jusqu'à .*, on l'a retiré\. Pourquoi \?$/
    )
    ;(arena.limits as Limits).destroy()
  })

  it('says the comparison goes random when a full model empties the pick', async () => {
    catalog.models = [{ id: 'full-id', name: 'GPT-5', status: 'enabled', lab, badges }]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['full-id']))
    arena.limits = createLimits({
      total: null,
      expensive: null,
      paused_llms: [{ id: 'full-id', until: '2026-10-14T22:00:00Z', reason: 'full' }]
    })

    const view = render(ViewPrompt, props)

    await view.findAllByText(/Complet aujourd'hui/)
    expect(view.container.querySelector('#pick-paused-notice')).toHaveTextContent(
      /^Complet aujourd'hui : on a retiré GPT-5 de votre sélection, la comparaison sera aléatoire\. Pourquoi \?$/
    )
  })

  it('takes a paused model out of a ?vs= link once the limits are read, back to random', async () => {
    catalog.models = [
      {
        id: 'expensive-id',
        human_id: 'gpt-5',
        name: 'GPT-5',
        status: 'enabled',
        lab,
        badges,
        params: 1000
      }
    ]
    arena.url = new URL('http://localhost/?vs=gpt-5')
    const limits = (arena.limits = createLimits())

    const view = render(ViewPrompt, props)
    await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('custom'))
    expect(view.container.querySelector('#pick-paused-notice')).toBeNull()

    vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent('expensive-id'))
    await limits.refresh()

    await vi.waitFor(() =>
      expect(view.container.querySelector('#pick-paused-notice')).toHaveTextContent(
        /GPT-5 est en pause pour vous .*, on l'a retiré, la comparaison sera aléatoire\./
      )
    )
    await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('random'))
    limits.destroy()
  })

  it('says a mode is paused before anyone sends when it has nothing left to draw', async () => {
    catalog.models = [
      { id: 'big-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'small-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
      { id: 'other-small-id', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
    ]
    localStorage.setItem('mode', 'big-vs-small')
    arena.limits = createLimits(expensiveSpent('big-id'))

    const view = render(ViewPrompt, props)
    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    const notice = view.container.querySelector('#pick-paused-notice')
    expect(notice).toHaveTextContent(
      /^Ce mode est en pause pour vous jusqu'à .*, choisissez-en un autre\./
    )
    expect(notice).not.toHaveFocus()
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeDisabled()

    await fireEvent.click(view.getByRole('radio', { name: /Aléatoire/, hidden: true }))
    expect(view.container.querySelector('#pick-paused-notice')).toBeNull()
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
    ;(arena.limits as Limits).destroy()
  })

  it('says a mode is full for today, not paused for the person, when its models are full', async () => {
    catalog.models = [
      { id: 'big-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'small-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
      { id: 'other-small-id', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
    ]
    localStorage.setItem('mode', 'big-vs-small')
    arena.limits = createLimits({
      total: null,
      expensive: null,
      paused_llms: [{ id: 'big-id', until: '2026-10-14T22:00:00Z', reason: 'full' }]
    })

    const view = render(ViewPrompt, props)
    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    const notice = view.container.querySelector('#pick-paused-notice')
    expect(notice).toHaveTextContent(
      /^Les modèles de ce mode ont reçu beaucoup de messages aujourd'hui : il revient demain, choisissez-en un autre\./
    )
    expect(notice).not.toHaveTextContent(/pour vous/)
  })

  it('says so when the refused pick empties the selection, and goes once the mode changes', async () => {
    const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0 }
    catalog.models = [{ id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab }]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id']))
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

    expect(await view.findByText(/la comparaison sera aléatoire/)).toBeInTheDocument()
    await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('random'))

    await fireEvent.click(view.getByRole('radio', { name: /Frugal/, hidden: true }))
    expect(view.container.querySelector('#pick-paused-notice')).toBeNull()
  })
})
