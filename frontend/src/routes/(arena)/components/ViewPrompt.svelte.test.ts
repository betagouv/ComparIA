import type { BotModel } from '$lib/models'
import { pickCurrentMode, type SelectionMode } from '$lib/selectionModes.svelte'
import { fireEvent, render } from '@testing-library/svelte'
import { flushSync } from 'svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ViewPrompt from './ViewPrompt.svelte'

// jsdom has no Web Animations API, which the dropdowns' fade-in needs.
Element.prototype.animate ??= vi.fn(() => ({
  cancel: vi.fn(),
  finished: Promise.resolve()
})) as unknown as Element['animate']

const fakes = vi.hoisted(() => ({ models: [] as unknown[], ctx: undefined as unknown }))

vi.mock('$lib/models', () => ({
  getModelsContext: () => ({ models: fakes.models })
}))

vi.mock('$lib/selectionModes.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/selectionModes.svelte')>()),
  getSelectionModesContext: () => fakes.ctx
}))

function model(id: string, name: string) {
  return {
    id,
    name,
    human_id: id,
    search: name.toLowerCase(),
    status: 'enabled',
    custom_selectable: true,
    lab: { id: 'lab', name: 'Lab', logo: undefined, has_custom_logo: false, logo_version: 0 },
    badges: {}
  } as unknown as BotModel
}

function mode(key: string, label: string, extra: Partial<SelectionMode> = {}): SelectionMode {
  return {
    key,
    label,
    short_label: label,
    description: null,
    icon: 'i-ri-dice-line',
    is_default: false,
    visitor_picks: 0,
    tools_policy: 'visitor',
    tool_keys: ['web_search', 'datagouv'],
    llm_ids: null,
    ...extra
  }
}

const tools = [
  { key: 'web_search', label: 'Recherche web', description: 'Chercher sur le web' },
  { key: 'datagouv', label: 'Données publiques', description: 'Jeux de données publics' }
]

const random = mode('random', 'Aléatoire', { is_default: true })
const custom = mode('custom', 'Sélection manuelle', { visitor_picks: 2, llm_ids: ['a', 'b'] })
const noTools = mode('legal', 'Juridique', { tools_policy: 'none', tool_keys: [] })
const forced = mode('search', 'Avec recherche', {
  tools_policy: 'forced',
  tool_keys: ['web_search']
})
const narrowed = mode('data', 'Données', { tool_keys: ['datagouv'] })

/** Same rules as initSelectionModesContext, without the fetch. */
function fakeModesContext(initial: SelectionMode[], stored = '') {
  const state = $state({ modes: initial, stored })
  return {
    get modes() {
      return state.modes
    },
    get current() {
      return pickCurrentMode(state.modes, state.stored)
    },
    get currentKey() {
      return pickCurrentMode(state.modes, state.stored).key
    },
    find: (key: string) => state.modes.find((m) => m.key === key),
    select: (key: string) => (state.stored = key),
    selectDefault: () => (state.stored = ''),
    refresh: vi.fn()
  }
}

const props = {
  loading: false,
  onPrompt: vi.fn(),
  suggestions: [],
  tools
}

type Queries = { getByRole: (role: string, options?: { name: string }) => HTMLElement }

async function send(view: Queries, text = 'Bonjour') {
  await fireEvent.input(view.getByRole('textbox'), { target: { value: text } })
  await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))
}

describe('ViewPrompt', () => {
  beforeEach(() => {
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear()
    })
    fakes.models = [model('a', 'Alpha'), model('b', 'Beta'), model('c', 'Gamma')]
    fakes.ctx = fakeModesContext([random, custom, noTools, forced, narrowed])
  })

  it('shows the submitted prompt and loading status while the first turn is pending', async () => {
    const onPrompt = vi.fn(() => new Promise<void>(() => {}))
    const view = render(ViewPrompt, { ...props, onPrompt })

    await send(view, 'Pourquoi le ciel est-il bleu ?')
    await fireEvent.click(view.getByRole('button', { name: 'Envoyer' }))

    expect(onPrompt).toHaveBeenCalledOnce()
    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ prompt_value: 'Pourquoi le ciel est-il bleu ?' })
    )

    await view.rerender({ ...props, onPrompt, loading: true })

    expect(view.getByText('Pourquoi le ciel est-il bleu ?')).toBeInTheDocument()
    expect(view.getByText('Aléatoire')).toBeInTheDocument()
    expect(view.getByRole('status')).toHaveTextContent('Chargement des réponses')
    expect(view.queryByRole('button', { name: 'Envoyer' })).toBeNull()
  })

  it('keeps a picking mode with nothing picked, so both models come from its pool', async () => {
    fakes.ctx = fakeModesContext([random, custom], 'custom')
    localStorage.setItem('customModelsSelection', '[]')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'custom', custom_models_selection: [] })
    )
  })

  it('sends the picked models that the mode allows', async () => {
    fakes.ctx = fakeModesContext([random, custom], 'custom')
    localStorage.setItem('customModelsSelection', '["c","a"]')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'custom', custom_models_selection: ['a'] })
    )
  })

  it('drops picked models and tools when switching to a mode that does not allow them', async () => {
    const ctx = fakeModesContext([random, custom, noTools], 'custom')
    fakes.ctx = ctx
    localStorage.setItem('customModelsSelection', '["a","b"]')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    ctx.select('legal')
    flushSync()
    ctx.select('custom')
    flushSync()
    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'custom', custom_models_selection: [], tools: [] })
    )
    expect(localStorage.getItem('customModelsSelection')).toBe('[]')
  })

  it('falls back to the default mode when the remembered one is gone', async () => {
    fakes.ctx = fakeModesContext([random, custom], 'big-vs-small')
    localStorage.setItem('customModelsSelection', '["a"]')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'random', custom_models_selection: [] })
    )
  })

  it('hides the tool picker and sends no tools in a mode without tools', async () => {
    fakes.ctx = fakeModesContext([random, noTools], 'legal')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    expect(view.container.querySelector('#dropdown-tools')).toBeNull()
    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(expect.objectContaining({ mode: 'legal', tools: [] }))
  })

  it('shows forced tools as locked and sends them', async () => {
    fakes.ctx = fakeModesContext([random, forced], 'search')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    expect(view.container.querySelector('#dropdown-tools')).toBeNull()
    expect(view.getByText(/Toujours actif dans ce mode/)).toBeInTheDocument()
    await send(view)

    expect(onPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ mode: 'search', tools: ['web_search'] })
    )
  })

  it('offers only the tools of the mode, and drops a picked tool it does not allow', async () => {
    fakes.ctx = fakeModesContext([random, narrowed], 'data')
    const onPrompt = vi.fn()
    const view = render(ViewPrompt, { ...props, onPrompt })

    expect(view.container.querySelector('#tool-web_search-dropdown')).toBeNull()
    expect(view.container.querySelector('#tool-datagouv-dropdown')).not.toBeNull()
    await send(view)

    // web_search is selected by default, but this mode does not offer it.
    expect(onPrompt).toHaveBeenCalledWith(expect.objectContaining({ mode: 'data', tools: [] }))
  })

  it('shows no mode menu when a single mode is on offer', () => {
    fakes.ctx = fakeModesContext([random])
    const view = render(ViewPrompt, props)

    expect(view.container.querySelector('#dropdown-mode')).toBeNull()
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
})
