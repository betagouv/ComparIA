import type { Mode } from '$lib/chatService.svelte'
import type { PausedLLM } from '$lib/generated/backend'
import type { BotModel } from '$lib/models'
import { expectNoDanglingAriaRefs, expectNoDuplicateIds } from '$lib/testing/a11y'
import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ModelSelector from './ModelSelector.svelte'
import type { ModePause } from './pausedModes'

const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0, name: 'Lab' }
function model(id: string, name: string) {
  return { id, name, lab, badges: {}, search: name.toLowerCase() } as unknown as BotModel
}
const models = [model('gpt', 'GPT-5'), model('gemma', 'Gemma 4'), model('gemini', 'Gemini 3.1 Pro')]
// Noon, and a pause that lifts later that day: the copy never says "demain",
// whatever the hour the tests run.
const NOON = new Date(2026, 9, 14, 12, 0)
const at = new Date(2026, 9, 14, 23, 59).toISOString()

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOON)
})
afterEach(() => vi.useRealTimers())

const paused = new Map<string, PausedLLM>([
  ['gpt', { id: 'gpt', until: at, reason: 'allowance' }],
  ['gemini', { id: 'gemini', until: '2026-10-15T00:00:00Z', reason: 'full' }]
])

// The model list fades in, and jsdom has no Web Animations.
Element.prototype.animate ??= function () {
  return { cancel() {}, finished: Promise.resolve(), onfinish: null } as unknown as Animation
}

async function openModels(props: Record<string, unknown> = {}) {
  const view = render(ModelSelector, {
    models,
    mode: 'random',
    modelsSelection: [],
    paused,
    ...props
  })
  await fireEvent.click(view.getByRole('radio', { name: /Sélection manuelle/, hidden: true }))
  return view
}

function card(choice: HTMLElement): HTMLElement {
  return choice.closest<HTMLElement>('.cg-border')!
}

describe('ModelSelector', () => {
  it('greys out a paused or full card, with a note saying until when', async () => {
    const view = await openModels()

    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })
    expect(card(gpt)).toHaveClass('cl-unavailable')
    // Still in the tab order, announced as unavailable with its note.
    expect(gpt).toBeEnabled()
    expect(gpt).toHaveAttribute('aria-disabled', 'true')
    expect(gpt).toHaveAccessibleDescription(/^En pause jusqu'à \d+\sh\s\d+$/)
    // The card's name stays the model's.
    expect(gpt).toHaveAccessibleName('Lab/GPT-5')
    const note = card(gpt).querySelector<HTMLElement>('.cl-pause-line')!
    expect(note).toHaveTextContent(/^En pause jusqu'à \d+\sh\s\d+$/)
    expect(note.querySelector('time')).toHaveAttribute('datetime', at)

    const gemini = view.getByRole('checkbox', { name: /Gemini/, hidden: true })
    expect(card(gemini)).toHaveClass('cl-unavailable')
    expect(gemini).toHaveAttribute('aria-disabled', 'true')
    expect(gemini).toHaveAccessibleDescription("Complet aujourd'hui")

    const gemma = view.getByRole('checkbox', { name: /Gemma/, hidden: true })
    expect(card(gemma)).not.toHaveClass('cl-unavailable')
    expect(gemma).not.toHaveAttribute('aria-disabled')
    expect(gemma).not.toHaveAccessibleDescription()
    expect(card(gemma).querySelector('.cl-pause-line')).toBeNull()

    // No "Pourquoi ?", nothing over the list.
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    expect(view.queryByRole('button', { name: 'Pourquoi ?', hidden: true })).toBeNull()
    expectNoDanglingAriaRefs(view.container)
    expectNoDuplicateIds(view.container)
  })

  it('keeps the models in their usual order, paused and full ones among the others', async () => {
    const view = await openModels()

    const names = view
      .getAllByRole('checkbox', { hidden: true })
      .map((box) => box.closest('label')!.querySelector('strong')!.textContent)
    expect(names).toEqual(['GPT-5', 'Gemma 4', 'Gemini 3.1 Pro'])
  })

  it('does not pick a greyed-out card, and a tap adds nothing to it', async () => {
    const view = await openModels()
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })
    const before = card(gpt).textContent

    await fireEvent.click(gpt)

    expect(gpt).not.toBeChecked()
    expect(view.getByText('0/2 modèles')).toBeInTheDocument()
    expect(card(gpt).textContent).toBe(before)

    await fireEvent.click(view.getByRole('checkbox', { name: /Gemma/, hidden: true }))
    expect(view.getByText('1/2 modèles')).toBeInTheDocument()
  })

  it('writes a time after midnight as "demain à 1 h 30"', async () => {
    const late = new Date(2026, 9, 15, 1, 30).toISOString()
    const view = await openModels({
      paused: new Map<string, PausedLLM>([['gpt', { id: 'gpt', until: late, reason: 'allowance' }]])
    })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })

    expect(card(gpt)).toHaveTextContent(/En pause jusqu'à demain à 1\sh\s30/)
  })

  it('greys out a mode with nothing to draw, and keeps the dialog open on it', async () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused,
      pausedModes: new Map<Mode, ModePause>([
        ['big-vs-small', { until: at, full: false }],
        ['small-models', { until: null, full: true }]
      ])
    })

    const mode = view.getByRole('radio', { name: /David contre Goliath/, hidden: true })
    expect(card(mode)).toHaveClass('cl-unavailable')
    expect(mode).toHaveAttribute('aria-disabled', 'true')
    expect(mode).toHaveAccessibleDescription(/^En pause jusqu'à \d+\sh\s\d+$/)
    expect(mode).toHaveAttribute('aria-controls', '')

    await fireEvent.click(mode)
    expect(mode).not.toBeChecked()

    const frugal = view.getByRole('radio', { name: /Frugal/, hidden: true })
    expect(frugal).toHaveAttribute('aria-disabled', 'true')
    expect(card(frugal)).toHaveTextContent(/Complet aujourd'hui$/)

    const random = view.getByRole('radio', { name: /Aléatoire/, hidden: true })
    expect(random).not.toHaveAttribute('aria-disabled')
    expect(card(random).querySelector('.cl-pause-line')).toBeNull()
    expectNoDanglingAriaRefs(view.container)
  })

  it('says nothing about the limits in random mode', () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused
    })

    expect(view.container).not.toHaveTextContent(/en pause|complet/i)
    expect(view.container.querySelector('.cl-pause-line, .cl-limit-hint')).toBeNull()
  })
})
