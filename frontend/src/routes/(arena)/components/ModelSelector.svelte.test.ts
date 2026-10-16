import type { Mode } from '$lib/chatService.svelte'
import type { PausedLLM } from '$lib/generated/backend'
import type { Spent } from '$lib/limits.svelte'
import type { BotModel } from '$lib/models'
import { expectNoDanglingAriaRefs } from '$lib/testing/a11y'
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

describe('ModelSelector', () => {
  it('shows a paused card with its time and reason, still reachable', async () => {
    const view = await openModels({ expensive: expensive('session') })

    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })
    expect(gpt).toBeEnabled()
    // Read like the others until tried.
    expect(gpt).not.toHaveAttribute('aria-disabled')
    expect(gpt).not.toHaveAccessibleDescription()
    expect(gpt).toHaveAccessibleName(/GPT-5 En pause · \d+\sh\s\d+/)
    expect(gpt.closest('label')!.querySelector('time')).toHaveAttribute('datetime', at)

    const gemini = view.getByRole('checkbox', { name: /Gemini/, hidden: true })
    expect(gemini).toHaveAccessibleName(/Complet · revient demain/)
    // Its own icon, not the pause one.
    expect(gemini.closest('label')!.querySelector('.i-ri-calendar-close-line')).not.toBeNull()

    const gemma = view.getByRole('checkbox', { name: /Gemma/, hidden: true })
    expect(gemma).not.toHaveAttribute('aria-disabled')
    // Nothing over the list counts them.
    expect(view.container.querySelector('#picker-paused-hint')).toBeNull()
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

  it('shows the reason inside a paused card once tapped, until another card is', async () => {
    const view = await openModels({ expensive: expensive('session') })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })
    const card = gpt.closest('label')!
    expect(card).not.toHaveTextContent(/Vous avez utilisé votre part/)

    await fireEvent.click(gpt)

    expect(card).toHaveTextContent(/Vous avez utilisé votre part de ce modèle\. Il revient à/)
    // Spoken through the live region, not added to the card's name.
    expect(gpt).toHaveAccessibleName(/^Lab\/GPT-5 En pause · \d+\sh\s\d+$/)
    await vi.waitFor(() =>
      expect(view.getAllByRole('status', { hidden: true }).at(-1)).toHaveTextContent(
        /^Vous avez utilisé votre part de ce modèle\. Il revient à \d+\sh\s\d+\.$/
      )
    )

    await fireEvent.click(view.getByRole('checkbox', { name: /Gemini/, hidden: true }))
    expect(card).not.toHaveTextContent(/Vous avez utilisé votre part/)
    expect(
      view.getByRole('checkbox', { name: /Gemini/, hidden: true }).closest('label')
    ).toHaveTextContent(/Ce modèle a reçu beaucoup de messages aujourd'hui/)

    await fireEvent.click(view.getByRole('checkbox', { name: /Gemma/, hidden: true }))
    expect(view.container.querySelector('.cl-selector__reason')).toBeNull()
  })

  it('writes a time after midnight as "demain à 1 h 30"', async () => {
    const late = new Date(2026, 9, 15, 1, 30).toISOString()
    const view = await openModels({
      expensive: { ...expensive('session'), resets_at: late },
      paused: new Map<string, PausedLLM>([['gpt', { id: 'gpt', until: late, reason: 'allowance' }]])
    })

    expect(view.getByRole('checkbox', { name: /GPT-5/, hidden: true })).toHaveAccessibleName(
      /En pause · demain à 1\sh\s30$/
    )
  })

  it('tells a network it has used its share', async () => {
    const view = await openModels({ expensive: expensive('network') })
    const gpt = view.getByRole('checkbox', { name: /GPT-5/, hidden: true })

    await fireEvent.click(gpt)

    expect(gpt.closest('label')).toHaveTextContent(/Votre réseau a utilisé sa part de ce modèle\./)
  })

  it('marks a mode with nothing left, and keeps the dialog open on it', () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused,
      expensive: expensive('session'),
      pausedModes: new Map<Mode, ModePause>([['big-vs-small', { until: at, full: false }]])
    })

    const mode = view.getByRole('radio', { name: /David contre Goliath/, hidden: true })
    expect(mode).not.toHaveAttribute('aria-disabled')
    expect(mode).not.toHaveAccessibleDescription()
    expect(mode).toHaveAttribute('aria-controls', '')
    // Nothing over the list says which modes are paused.
    expect(view.container.querySelector('#modes-paused-hint')).toBeNull()
  })
})
