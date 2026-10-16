import { api } from '$lib/fastapi-client'
import type { ArenaLimits } from '$lib/generated/backend'
import type { PickRefusal } from '$lib/chatService.svelte'
import { createLimits, type Limits, type Spent } from '$lib/limits.svelte'
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
      value: 'custom',
      icon: 'i-ri-search-line',
      title: 'Sélection manuelle',
      label: 'Sélection manuelle',
      alt_label: 'Sélection manuelle',
      description: 'Choisissez les modèles'
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
    signed_in_factor: 3,
    paused_llms: ids.map((id) => ({ id, until: null, reason: 'allowance' as const }))
  }
}

// A send refused on a model paused or filled since the page read the limits.
function refusal(
  detail: PickRefusal['detail'] = 'expensive_allowance_spent',
  scope: 'session' | null = 'session'
): PickRefusal {
  return {
    detail,
    limit: {
      scope,
      resets_at: new Date(Date.now() + 3600_000).toISOString(),
      resets_in: 3600,
      llm_ids: ['expensive-id']
    }
  }
}

function spentPause(): Spent {
  const liftsAt = Date.now() + 3600_000
  return { scope: 'session', resets_at: new Date(liftsAt).toISOString(), resets_in: 3600, liftsAt }
}

// What the page says outside the mode and model lists, where greyed-out
// cards carry their own notes.
const UNSAID = /on l'a retiré|en pause|\bcomplet\b|comparaison sera aléatoire|Pourquoi/i
function underPrompt(view: { container: HTMLElement }): string {
  const page = view.container.cloneNode(true) as HTMLElement
  page.querySelectorAll('dialog').forEach((dialog) => dialog.remove())
  return page.textContent ?? ''
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
      scope: 'network' as const,
      resets_at: new Date(Date.now() + 3600_000).toISOString(),
      resets_in: 3600,
      liftsAt: Date.now() + 3600_000
    }
    await view.rerender({ ...props, pause })

    expect(view.queryByRole('textbox')).toBeNull()
    expect(
      view.getByText(
        /^Beaucoup de messages sont partis de votre réseau .* vous pouvez voir le classement ou découvrir les modèles\.$/
      )
    ).toBeInTheDocument()
    expect(view.getByRole('link', { name: 'Voir le classement' })).toHaveAttribute(
      'href',
      '/ranking'
    )
    expect(view.getByRole('link', { name: 'Découvrir les modèles' })).toHaveAttribute(
      'href',
      '/models'
    )
    // Shown before anyone sent from here: part of the page, focus stays.
    expect(
      view.getByRole('heading', { name: /^Vous pourrez écrire à nouveau à/ })
    ).not.toHaveFocus()
    // The card's title takes the place of the page's question, which would
    // invite typing.
    expect(
      view.getByRole('heading', { level: 2, name: /^Vous pourrez écrire à nouveau à/ })
    ).toBeInTheDocument()
    expect(view.queryByRole('heading', { name: /Comment puis-je vous aider/ })).toBeNull()

    await view.rerender({ ...props, pause: undefined })
    expect(view.getByRole('textbox')).toHaveValue('Ma question')
    expect(
      view.getByRole('heading', { level: 2, name: /Comment puis-je vous aider/ })
    ).toBeInTheDocument()
  })

  it.each([
    ['expensive_allowance_spent' as const, 'session' as const],
    ['model_full_today' as const, null]
  ])(
    'sends again, once, without a model refused as it was just paused (%s)',
    async (detail, scope) => {
      catalog.models = [
        { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
        { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 }
      ]
      localStorage.setItem('mode', 'custom')
      localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
      const read = vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent('expensive-id'))
      const onPrompt = vi.fn(async () => {
        // Refused the first time only.
        const refused = onPrompt.mock.calls.length === 1 ? refusal(detail, scope) : undefined
        await view.rerender({ ...props, onPrompt, pickRefusal: refused })
      })
      const view = render(ViewPrompt, { ...props, onPrompt })

      await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
      await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

      await vi.waitFor(() => expect(onPrompt).toHaveBeenCalledTimes(2))
      // The limits read again, the same message, the refused model taken out.
      expect(read).toHaveBeenCalledWith('/arena/limits', expect.anything())
      expect(onPrompt).toHaveBeenLastCalledWith(
        expect.objectContaining({
          prompt_value: 'Ma question',
          mode: 'custom',
          custom_models_selection: ['cheap-id']
        })
      )
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
      expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
      expect(underPrompt(view)).not.toMatch(UNSAID)
      read.mockRestore()
    }
  )

  it('sends a saved mode emptied since as random, once', async () => {
    catalog.models = [
      { id: 'big-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'small-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
      { id: 'other-small-id', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
    ]
    localStorage.setItem('mode', 'big-vs-small')
    const read = vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent('big-id'))
    const onPrompt = vi.fn(async () => {
      const refused =
        onPrompt.mock.calls.length === 1
          ? { ...refusal(), limit: { ...refusal().limit, llm_ids: undefined } }
          : undefined
      await view.rerender({ ...props, onPrompt, pickRefusal: refused })
    })
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    await vi.waitFor(() => expect(onPrompt).toHaveBeenCalledTimes(2))
    expect(onPrompt.mock.calls[0]).toEqual([expect.objectContaining({ mode: 'big-vs-small' })])
    expect(onPrompt).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'random' }))
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    read.mockRestore()
  })

  it('says so in one line, and stops, when the send again is refused too', async () => {
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'other-id', name: 'Kimi K3', status: 'enabled', lab, badges, params: 1000 },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'other-id']))
    // The read still says nothing is paused: only the refusals tell.
    const read = vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent())
    const onPrompt = vi.fn(async () => {
      const ids = onPrompt.mock.calls.length === 1 ? ['expensive-id'] : ['other-id']
      const refused = { ...refusal(), limit: { ...refusal().limit, llm_ids: ids } }
      await view.rerender({ ...props, onPrompt, pickRefusal: refused })
    })
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    const line = await vi.waitFor(() => {
      const line = view.container.querySelector<HTMLElement>('#raced-hint')
      expect(line).not.toBeNull()
      return line!
    })
    expect(line).toHaveTextContent(/^Ce modèle vient d'être mis en pause, réessayez\.$/)
    expect(line).toHaveFocus()
    expect(line.querySelector('.i-ri-time-line')).not.toBeNull()
    // Twice, never more.
    expect(onPrompt).toHaveBeenCalledTimes(2)
    expect(onPrompt).toHaveBeenLastCalledWith(
      expect.objectContaining({ custom_models_selection: ['other-id'] })
    )
    // Both refused models out: the next Envoyer goes random.
    expect(localStorage.getItem('mode')).toBe('random')
    expect(view.getByRole('textbox')).toHaveValue('Ma question')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()

    // Gone once the person picks for themselves.
    await fireEvent.click(view.getByRole('radio', { name: /Frugal/, hidden: true }))
    expect(view.container.querySelector('#raced-hint')).toBeNull()
    read.mockRestore()
  })

  it.each([
    ['the whole allowance spent', { pause: spentPause() }],
    ['too many messages at once', { busyHint: 'Beaucoup de messages partent de votre réseau.' }],
    ['an error in the prompt', { promptError: 'Réessayez' }]
  ])('does not send again on %s', async (_, answer) => {
    catalog.models = [{ id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges }]
    const read = vi.spyOn(api, 'request')
    const onPrompt = vi.fn(async () => {
      await view.rerender({ ...props, onPrompt, ...answer })
    })
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))
    await vi.waitFor(() => expect(onPrompt).toHaveBeenCalledOnce())
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(onPrompt).toHaveBeenCalledOnce()
    expect(read).not.toHaveBeenCalled()
    expect(view.container.querySelector('#raced-hint')).toBeNull()
    read.mockRestore()
  })

  it('asks to send again shortly when too many messages went at once', async () => {
    const view = render(ViewPrompt, {
      ...props,
      busyHint:
        'Beaucoup de messages partent de votre réseau en ce moment. Renvoyez le vôtre dans quelques secondes.'
    })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    // Told like the other limits, under the controls, with its own icon, and
    // focused since the send did not start.
    const hint = view.container.querySelector<HTMLElement>('#busy-hint')!
    expect(hint).toHaveTextContent(/^Beaucoup de messages partent de votre réseau en ce moment\./)
    expect(hint).toHaveFocus()
    expect(hint.querySelector('.i-ri-time-line')).not.toBeNull()
    expect(hint).not.toHaveTextContent('Pourquoi')
    expect(view.getByRole('textbox')).not.toHaveAccessibleDescription(/Beaucoup de messages/)
    // A hint, not an error in what was typed: sending stays open.
    expect(view.getByRole('textbox')).not.toHaveAttribute('aria-invalid', 'true')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
  })

  it('takes a saved pick paused since out of the selection, unsaid, before anyone sends', async () => {
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 }
    ]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id', 'cheap-id']))
    arena.limits = createLimits(expensiveSpent('expensive-id'))

    const view = render(ViewPrompt, props)

    await vi.waitFor(() =>
      expect(localStorage.getItem('customModelsSelection')).toBe('["cheap-id"]')
    )
    expect(localStorage.getItem('mode')).toBe('custom')
    // The selector shows what is left; nothing under the prompt, nor for a
    // screen reader.
    expect(view.getByRole('button', { name: /Gemma 4\s*VS\s*Aléatoire/ })).toBeInTheDocument()
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    expect(underPrompt(view)).not.toMatch(UNSAID)
    expect(view.getAllByRole('status')[0].textContent).toBe('')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeInTheDocument()
    ;(arena.limits as Limits).destroy()
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

  it('goes random, unsaid, when a full model empties the pick', async () => {
    catalog.models = [{ id: 'full-id', name: 'GPT-5', status: 'enabled', lab, badges }]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['full-id']))
    arena.limits = createLimits({
      total: null,
      expensive: null,
      signed_in_factor: 3,
      paused_llms: [{ id: 'full-id', until: '2026-10-14T22:00:00Z', reason: 'full' }]
    })

    const view = render(ViewPrompt, props)

    await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('random'))
    expect(localStorage.getItem('customModelsSelection')).toBe('[]')
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    expect(underPrompt(view)).not.toMatch(UNSAID)
    ;(arena.limits as Limits).destroy()
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

    vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent('expensive-id'))
    await limits.refresh()

    await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('random'))
    expect(localStorage.getItem('customModelsSelection')).toBe('[]')
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    limits.destroy()
  })

  it.each([
    ['paused for the person', expensiveSpent('big-id')],
    [
      'full for the day',
      {
        total: null,
        expensive: null,
        signed_in_factor: 3,
        paused_llms: [{ id: 'big-id', until: '2026-10-14T22:00:00Z', reason: 'full' as const }]
      }
    ]
  ])(
    'goes back to random, unsaid, when a saved mode has nothing left to draw (%s)',
    async (_, read: ArenaLimits) => {
      catalog.models = [
        { id: 'big-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
        { id: 'small-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
        { id: 'other-small-id', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
      ]
      localStorage.setItem('mode', 'big-vs-small')
      arena.limits = createLimits(read)

      const view = render(ViewPrompt, props)
      await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

      await vi.waitFor(() => expect(localStorage.getItem('mode')).toBe('random'))
      expect(view.getByRole('radio', { name: /Aléatoire/, hidden: true })).toBeChecked()
      // Envoyer works, and nothing under the prompt tells of the mode.
      expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
      expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
      expect(view.queryByText(/Changer de mode|choisissez-en un autre/)).toBeNull()
      expect(view.getAllByRole('status')[0].textContent).toBe('')
      // Its card in the mode list is the one place that says so.
      expect(
        view.getByRole('radio', { name: /David contre Goliath/, hidden: true })
      ).toHaveAttribute('aria-disabled', 'true')
      ;(arena.limits as Limits).destroy()
    }
  )

  it('sends again as random when the refused pick empties the selection', async () => {
    catalog.models = [{ id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges }]
    localStorage.setItem('mode', 'custom')
    localStorage.setItem('customModelsSelection', JSON.stringify(['expensive-id']))
    const read = vi.spyOn(api, 'request').mockResolvedValue(expensiveSpent('expensive-id'))
    const onPrompt = vi.fn(async () => {
      const refused = onPrompt.mock.calls.length === 1 ? refusal() : undefined
      await view.rerender({ ...props, onPrompt, pickRefusal: refused })
    })
    const view = render(ViewPrompt, { ...props, onPrompt })

    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    await vi.waitFor(() => expect(onPrompt).toHaveBeenCalledTimes(2))
    expect(onPrompt).toHaveBeenLastCalledWith(
      expect.objectContaining({ mode: 'random', custom_models_selection: [] })
    )
    expect(underPrompt(view)).not.toMatch(UNSAID)
    read.mockRestore()
  })

  it('says nothing in random mode once the expensive allowance is spent', async () => {
    // A big model left open, as in the catalog: every mode still draws, so
    // the mode list greys none out.
    catalog.models = [
      { id: 'expensive-id', name: 'GPT-5', status: 'enabled', lab, badges, params: 1000 },
      { id: 'big-open-id', name: 'Llama 4', status: 'enabled', lab, badges, params: 400 },
      { id: 'cheap-id', name: 'Gemma 4', status: 'enabled', lab, badges, params: 30 },
      { id: 'other-cheap-id', name: 'Mistral Small', status: 'enabled', lab, badges, params: 24 }
    ]
    arena.limits = createLimits(expensiveSpent('expensive-id'))

    const view = render(ViewPrompt, props)
    await fireEvent.input(view.getByRole('textbox'), { target: { value: 'Ma question' } })

    // The draw leaves the expensive models out on its own.
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    expect(view.container).not.toHaveTextContent(/en pause|\bcomplet\b/i)
    expect(view.getAllByRole('status')[0].textContent).toBe('')
    expect(view.getByRole('button', { name: 'Envoyer' })).toBeEnabled()
    ;(arena.limits as Limits).destroy()
  })
})
