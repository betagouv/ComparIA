import type { Mode } from '$lib/chatService.svelte'
import type { PausedLLM } from '$lib/generated/backend'
import type { Spent } from '$lib/limits.svelte'
import type { BotModel } from '$lib/models'
import { expectNoDanglingAriaRefs } from '$lib/testing/a11y'
import { fireEvent, render, within } from '@testing-library/svelte'
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

function expensive(scope: Spent['scope']): Spent {
  return { scope, resets_at: at, resets_in: 3600, liftsAt: NOON.getTime() + 3600_000 }
}
const paused = new Map<string, PausedLLM>([
  ['gpt', { id: 'gpt', until: at, reason: 'allowance' }],
  ['gemini', { id: 'gemini', until: '2026-10-15T00:00:00Z', reason: 'full' }]
])

// The model list fades in, and jsdom has no Web Animations.
Element.prototype.animate ??= function () {
  return { cancel() {}, finished: Promise.resolve(), onfinish: null } as unknown as Animation
}

async function openModels(props: Record<string, unknown>) {
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

// The selector's live region, not the toggletips' own.
function said(view: { container: HTMLElement }, selector: string) {
  return view.container.querySelector(`#${selector} + p[role="status"]`)!
}

describe('ModelSelector', () => {
  it('shows a paused or full card like any other until it is tried', async () => {
    const view = await openModels({ expensive: expensive('session') })

    for (const name of [/GPT-5/, /Gemini/, /Gemma/]) {
      const box = view.getByRole('checkbox', { name, hidden: true })
      expect(box).toBeEnabled()
      expect(box).not.toHaveAttribute('aria-disabled')
      expect(box).not.toHaveAccessibleDescription()
      expect(card(box)).not.toHaveTextContent(/pause|Complet/i)
      expect(card(box).querySelector('time, button')).toBeNull()
    }
    // Nothing over the list counts them, and nothing is said yet.
    expect(view.container.querySelector('.cl-limit-hint')).toBeNull()
    expect(view.container).not.toHaveTextContent(/en pause|complet/i)
    expect(said(view, 'models-selector').textContent).toBe('')
    expectNoDanglingAriaRefs(view.container)
  })

  it('keeps the models in their usual order, paused and full ones among the others', async () => {
    const view = await openModels({ expensive: expensive('session') })

    const names = view
      .getAllByRole('checkbox', { hidden: true })
      .map((box) => box.closest('label')!.querySelector('strong')!.textContent)
    expect(names).toEqual(['GPT-5', 'Gemma 4', 'Gemini 3.1 Pro'])
  })

  it('does not pick a paused card', async () => {
    const view = await openModels({ expensive: expensive('session') })

    await fireEvent.click(view.getByRole('checkbox', { name: /GPT-5/, hidden: true }))

    expect(view.getByRole('checkbox', { name: /GPT-5/, hidden: true })).not.toBeChecked()
    expect(view.getByText('0/2 modèles')).toBeInTheDocument()
  })

  it('says in a tapped card until when it is paused, and why, until another card is', async () => {
    const view = await openModels({ expensive: expensive('session') })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })

    await fireEvent.click(gpt)

    const line = card(gpt).querySelector<HTMLElement>('.cl-pause-line')!
    expect(line).toHaveTextContent(/^En pause pour vous jusqu'à \d+\sh\s\d+ Pourquoi \?$/)
    expect(line.querySelector('time')).toHaveAttribute('datetime', at)
    // Outside the label: the card's name stays the model's.
    expect(gpt).toHaveAccessibleName('Lab/GPT-5')
    // Spoken as it shows.
    await vi.waitFor(() =>
      expect(said(view, 'models-selector')).toHaveTextContent(
        /^En pause pour vous jusqu'à \d+\sh\s\d+$/
      )
    )
    await fireEvent.click(within(line).getByRole('button', { name: 'Pourquoi ?', hidden: true }))
    expect(line).toHaveTextContent(/chacun peut envoyer un nombre limité de messages/)

    const gemini = view.getByRole('checkbox', { name: /Gemini/, hidden: true })
    await fireEvent.click(gemini)
    expect(card(gpt).querySelector('.cl-pause-line')).toBeNull()
    expect(card(gemini).querySelector('.cl-pause-line')).toHaveTextContent(
      /^Complet aujourd'hui, revient demain Pourquoi \?$/
    )

    await fireEvent.click(view.getByRole('checkbox', { name: /Gemma/, hidden: true }))
    expect(view.container.querySelector('.cl-pause-line')).toBeNull()
    expectNoDanglingAriaRefs(view.container)
  })

  it('writes a time after midnight as "demain à 1 h 30"', async () => {
    const late = new Date(2026, 9, 15, 1, 30).toISOString()
    const view = await openModels({
      expensive: { ...expensive('session'), resets_at: late },
      paused: new Map<string, PausedLLM>([['gpt', { id: 'gpt', until: late, reason: 'allowance' }]])
    })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })

    await fireEvent.click(gpt)

    expect(card(gpt)).toHaveTextContent(/En pause pour vous jusqu'à demain à 1\sh\s30/)
  })

  it('tells a network it has used its share', async () => {
    const view = await openModels({ expensive: expensive('network') })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })

    await fireEvent.click(gpt)

    expect(card(gpt)).toHaveTextContent(/En pause pour votre réseau jusqu'à/)
  })

  it('says a mode is paused only once tried, and keeps the dialog open on it', async () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused,
      expensive: expensive('session'),
      pausedModes: new Map<Mode, ModePause>([
        ['big-vs-small', { until: at, full: false }],
        ['small-models', { until: null, full: true }]
      ])
    })

    const mode = view.getByRole('radio', { name: /David contre Goliath/, hidden: true })
    expect(mode).not.toHaveAttribute('aria-disabled')
    expect(mode).not.toHaveAccessibleDescription()
    expect(mode).toHaveAttribute('aria-controls', '')
    expect(view.container).not.toHaveTextContent(/en pause|complet/i)

    await fireEvent.click(mode)

    expect(mode).not.toBeChecked()
    expect(card(mode)).toHaveTextContent(/En pause pour vous jusqu'à \d+\sh\s\d+ Pourquoi \?$/)
    await vi.waitFor(() =>
      expect(said(view, 'mode-selector')).toHaveTextContent(/^En pause pour vous jusqu'à/)
    )

    const frugal = view.getByRole('radio', { name: /Frugal/, hidden: true })
    await fireEvent.click(frugal)
    expect(card(frugal)).toHaveTextContent(/Complet aujourd'hui, revient demain Pourquoi \?$/)
    expect(card(mode).querySelector('.cl-pause-line')).toBeNull()
  })

  it('says nothing about the limits in random mode', () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused,
      expensive: expensive('session')
    })

    expect(view.container).not.toHaveTextContent(/en pause|complet/i)
    expect(view.container.querySelector('.cl-pause-line, .cl-limit-hint')).toBeNull()
  })
})
