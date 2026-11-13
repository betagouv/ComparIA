import { m } from '$lib/i18n/messages'
import type { BotModel } from '$lib/models'
import type { SelectionMode } from '$lib/selectionModes.svelte'
import { fireEvent, render, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ModelSelector from './ModelSelector.svelte'

const toast = vi.hoisted(() => vi.fn())
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: toast }))

// jsdom has no Web Animations API, which the picker's fade-in needs.
Element.prototype.animate ??= vi.fn(() => ({
  cancel: vi.fn(),
  finished: Promise.resolve()
})) as unknown as Element['animate']

function model(id: string, name: string, customSelectable = true) {
  return {
    id,
    name,
    human_id: id,
    search: name.toLowerCase(),
    status: 'enabled',
    custom_selectable: customSelectable,
    lab: { id: 'lab', name: 'Lab', logo: undefined, has_custom_logo: false, logo_version: 0 },
    badges: {}
  } as unknown as BotModel
}

function mode(key: string, label: string, extra: Partial<SelectionMode> = {}): SelectionMode {
  return {
    key,
    label,
    short_label: `${label} (bouton)`,
    description: `Description ${label}`,
    icon: 'i-ri-dice-line',
    is_default: false,
    visitor_picks: 0,
    tools_policy: 'visitor',
    tool_keys: [],
    llm_ids: null,
    ...extra
  }
}

const models = [model('a', 'Alpha'), model('b', 'Beta'), model('c', 'Gamma')]
const random = mode('random', 'Hasard', { is_default: true })
const pickTwo = mode('custom', 'Au choix', { visitor_picks: 2, llm_ids: ['a', 'b', 'c'] })
const pickOne = mode('champion', 'Champion', { visitor_picks: 1, llm_ids: ['a', 'b'] })

function modelChoices(container: HTMLElement) {
  const group = container.ownerDocument.getElementById('models-selector')!
  return within(group).queryAllByRole('checkbox', { hidden: true })
}

describe('ModelSelector', () => {
  beforeEach(() => toast.mockReset())

  it('lists the modes it is given, with the short label on the closed button', () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickTwo],
      mode: 'random',
      modelsSelection: []
    })

    expect(view.getByRole('button', { name: /Hasard \(bouton\)/ })).toBeInTheDocument()
    expect(view.getByRole('menuitem', { name: /Hasard/, hidden: true })).toBeChecked()
    expect(view.getByRole('menuitem', { name: /Au choix/, hidden: true })).toBeInTheDocument()
    expect(view.getByText('Description Au choix')).toBeInTheDocument()
  })

  it('shows no mode menu when a single blind mode is on offer', () => {
    const view = render(ModelSelector, {
      models,
      modes: [random],
      mode: 'random',
      modelsSelection: []
    })

    expect(view.queryByRole('menuitem', { hidden: true })).toBeNull()
    expect(view.queryByRole('button')).toBeNull()
  })

  it('goes straight to the pick button when the single mode lets the visitor pick', () => {
    const view = render(ModelSelector, {
      models,
      modes: [pickTwo],
      mode: 'custom',
      modelsSelection: []
    })

    expect(view.queryByRole('menuitem', { hidden: true })).toBeNull()
    const pick = view.getByRole('button', { name: m['arenaHome.compareModels.pickTwo']() })
    expect(pick).toHaveAttribute('aria-controls', 'modal-models-selection')
  })

  it('opens the model picker from a mode that lets the visitor pick', () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickTwo],
      mode: 'random',
      modelsSelection: []
    })

    expect(view.getByRole('menuitem', { name: /Au choix/, hidden: true })).toHaveAttribute(
      'aria-controls',
      'modal-models-selection'
    )
    expect(view.getByRole('menuitem', { name: /Hasard/, hidden: true })).toHaveAttribute(
      'aria-controls',
      ''
    )
  })

  it("lists only the mode's own models", () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickOne],
      mode: 'champion',
      modelsSelection: []
    })

    const choices = modelChoices(view.container)
    expect(choices.map((input) => (input as HTMLInputElement).value)).toEqual(['a', 'b'])
  })

  it('greys a locked model of the pool rather than hiding it', () => {
    const locked = model('d', 'Delta', false)
    const view = render(ModelSelector, {
      models: [...models, locked],
      modes: [random, mode('pool', 'Pool', { visitor_picks: 2, llm_ids: ['a', 'd'] })],
      mode: 'pool',
      modelsSelection: []
    })

    const [alpha, delta] = modelChoices(view.container)
    expect((delta as HTMLInputElement).value).toBe('d')
    expect(delta).toBeDisabled()
    expect(alpha).toBeEnabled()
    expect(view.getByText('Disponible au hasard uniquement')).toBeInTheDocument()
  })

  it('in a mode with two pools, greys what cannot face the first pick', () => {
    const split = mode('split', 'Split', {
      visitor_picks: 2,
      llm_ids: ['a', 'b', 'c'],
      llm_ids_a: ['a'],
      llm_ids_b: ['b', 'c']
    })
    const view = render(ModelSelector, {
      models,
      modes: [random, split],
      mode: 'split',
      modelsSelection: ['b']
    })

    const [alpha, beta, gamma] = modelChoices(view.container)
    expect(alpha).toBeEnabled()
    expect(beta).toBeChecked()
    expect(gamma).toBeDisabled()
    expect(
      view.getByText('Ne peut pas affronter le modèle choisi dans ce mode')
    ).toBeInTheDocument()
  })

  it('stops at one model in a mode with a single pick, and draws the other', () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickOne],
      mode: 'champion',
      modelsSelection: ['a']
    })

    const [alpha, beta] = modelChoices(view.container)
    expect(alpha).toBeChecked()
    expect(beta).toBeDisabled()
    expect(view.getByText('1/1 modèles')).toBeInTheDocument()
    expect(view.getByRole('button', { name: /Alpha\s*VS\s*Aléatoire/ })).toBeInTheDocument()
  })

  it('allows two models in a mode with two picks', () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickTwo],
      mode: 'custom',
      modelsSelection: ['a']
    })

    const [, beta, gamma] = modelChoices(view.container)
    expect(beta).toBeEnabled()
    expect(gamma).toBeEnabled()
    expect(view.getByText('1/2 modèles')).toBeInTheDocument()
  })

  it('says both models will be drawn when the picker closes with nothing picked', async () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickTwo],
      mode: 'custom',
      modelsSelection: []
    })

    await fireEvent(
      view.container.ownerDocument.getElementById('modal-models-selection')!,
      new Event('dsfr.conceal')
    )

    expect(view.getByRole('menuitem', { name: /Au choix/, hidden: true })).toBeChecked()
    expect(toast).toHaveBeenCalledWith(
      'Aucun modèle choisi : la comparaison se fera entre deux modèles aléatoires.',
      5000
    )
  })

  it('stays quiet when the picker closes with a model picked', async () => {
    const view = render(ModelSelector, {
      models,
      modes: [random, pickTwo],
      mode: 'custom',
      modelsSelection: ['a']
    })

    await fireEvent(
      view.container.ownerDocument.getElementById('modal-models-selection')!,
      new Event('dsfr.conceal')
    )

    expect(toast).not.toHaveBeenCalled()
  })
})
