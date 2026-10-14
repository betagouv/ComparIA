import type { Mode } from '$lib/chatService.svelte'
import type { PausedModel, Spent } from '$lib/limits.svelte'
import type { BotModel } from '$lib/models'
import { expectNoDanglingAriaRefs } from '$lib/testing/a11y'
import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import ModelSelector from './ModelSelector.svelte'

const lab = { logo: '', has_custom_logo: false, id: 'lab', logo_version: 0, name: 'Lab' }
function model(id: string, name: string) {
  return { id, name, lab, badges: {}, search: name.toLowerCase() } as unknown as BotModel
}
const models = [model('gpt', 'GPT-5'), model('gemma', 'Gemma 4'), model('gemini', 'Gemini 3.1 Pro')]
// Later today at whatever hour this runs, so the copy never says "demain".
const at = new Date(new Date().setHours(23, 59, 0, 0)).toISOString()

function expensive(scope: Spent['scope']): Spent {
  return { scope, resets_at: at, resets_in: 3600, liftsAt: Date.now() + 3600_000 }
}
const paused = new Map<string, PausedModel>([
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
    expect(gpt).toHaveAttribute('aria-disabled', 'true')
    expect(gpt).toHaveAccessibleName(/GPT-5 En pause · \d+\sh\s\d+/)
    expect(gpt).toHaveAccessibleDescription(
      /^Vous avez utilisé votre part de ce modèle\. Il revient à \d+\sh\s\d+\.$/
    )
    expect(gpt.closest('label')!.querySelector('time')).toHaveAttribute('datetime', at)

    const gemini = view.getByRole('checkbox', { name: /Gemini/, hidden: true })
    expect(gemini).toHaveAccessibleName(/Complet aujourd'hui/)
    expect(gemini).toHaveAccessibleDescription(/Il revient demain\./)

    const gemma = view.getByRole('checkbox', { name: /Gemma/, hidden: true })
    expect(gemma).not.toHaveAttribute('aria-disabled')
    // One model paused for an allowance: the full one is not counted.
    const hint = view.container.querySelector('#picker-paused-hint')!
    expect(hint).toHaveTextContent(
      /^1 modèle en pause pour vous jusqu'à \d+\sh\s\d+\. Pourquoi \?$/
    )
    await fireEvent.click(view.getByRole('button', { name: 'Pourquoi ?', hidden: true }))
    expect(hint).toHaveTextContent(/chacun peut envoyer un nombre limité de messages/)
    expectNoDanglingAriaRefs(view.container)
  })

  it('does not pick a paused card', async () => {
    const view = await openModels({ expensive: expensive('session') })

    await fireEvent.click(view.getByRole('checkbox', { name: /GPT-5/, hidden: true }))

    expect(view.getByRole('checkbox', { name: /GPT-5/, hidden: true })).not.toBeChecked()
    expect(view.getByText('0/2 modèles')).toBeInTheDocument()
  })

  it('counts the models paused for the allowance, not the full ones', async () => {
    const two = new Map<string, PausedModel>([
      ...paused,
      ['gemma', { id: 'gemma', until: at, reason: 'allowance' }]
    ])
    const view = await openModels({ expensive: expensive('session'), paused: two })

    expect(view.container.querySelector('#picker-paused-hint')).toHaveTextContent(
      /^2 modèles en pause pour vous/
    )
  })

  it('says nothing in the header when only full models are paused', async () => {
    const full = new Map([...paused].filter(([, llm]) => llm.reason === 'full'))
    const view = await openModels({ expensive: undefined, paused: full })

    expect(view.container.querySelector('#picker-paused-hint')).toBeNull()
  })

  it('tells a network it has used its share', async () => {
    const view = await openModels({ expensive: expensive('network') })

    expect(view.container.querySelector('#picker-paused-hint')).toHaveTextContent(
      /pour votre réseau/
    )
    expect(view.getByRole('checkbox', { name: /GPT-5/, hidden: true })).toHaveAccessibleDescription(
      /^Votre réseau a utilisé sa part de ce modèle\./
    )
  })

  it('marks a mode with nothing left, and keeps the dialog open on it', () => {
    const view = render(ModelSelector, {
      models,
      mode: 'random',
      modelsSelection: [],
      paused,
      expensive: expensive('session'),
      pausedModes: new Map<Mode, string | null>([['big-vs-small', at]])
    })

    const mode = view.getByRole('radio', { name: /David contre Goliath/, hidden: true })
    expect(mode).toHaveAttribute('aria-disabled', 'true')
    expect(mode).toHaveAttribute('aria-controls', '')
    expect(mode).toHaveAccessibleDescription(
      /^Ce mode a besoin de modèles qui sont en pause pour vous\. Il revient à \d+\sh\s\d+\.$/
    )
    expect(view.getByRole('radio', { name: /Frugal/, hidden: true })).not.toHaveAttribute(
      'aria-disabled'
    )
  })
})
