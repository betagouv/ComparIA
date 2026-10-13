import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ViewChat from './ViewChat.svelte'

const comparator = vi.hoisted(() => ({
  comparison: { id: 'comparison-id', mode: 'random', revealed: false, turns: [] },
  comparisonId: 'comparison-id',
  status: 'complete',
  loading: false,
  error: undefined,
  canReveal: true,
  promptError: undefined as string | undefined,
  pause: undefined as unknown,
  promptWarnings: undefined,
  reveal: vi.fn(),
  ask: vi.fn(),
  retry: vi.fn(),
  vote: vi.fn(),
  sendAnyway: vi.fn(),
  dismissWarnings: vi.fn()
}))

vi.mock('$lib/chatService.svelte', () => ({
  getComparison: () => comparator,
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

const props = { comparisonId: 'comparison-id', runAfterAcceptance: vi.fn() }
const revealLabel = 'Terminer et découvrir les modèles'

describe('ViewChat', () => {
  it('keeps the reveal usable after a refused message', async () => {
    // A refusal turns the comparison status to 'error'; it must not lock the
    // reveal, which used to do nothing at all when clicked.
    Object.assign(comparator, { status: 'error', promptError: 'Trop de messages bloqués' })
    const view = render(ViewChat, props)
    const reveal = view.getByRole('button', { name: revealLabel })

    expect(reveal).not.toHaveAttribute('aria-disabled', 'true')
    await fireEvent.click(reveal)
    expect(comparator.reveal).toHaveBeenCalledOnce()
    Object.assign(comparator, { status: 'complete', promptError: undefined })
  })

  it('puts the pause notice in place of the text box and moves focus to its title', async () => {
    comparator.pause = {
      detail: 'allowance_spent',
      limit: {
        scope: 'session',
        resets_at: new Date(Date.now() + 3600_000).toISOString(),
        resets_in: 3600,
        llm_ids: []
      }
    }
    const view = render(ViewChat, props)

    expect(view.queryByRole('textbox')).toBeNull()
    const title = view.getByRole('heading', { name: /^Pause jusqu'à/ })
    expect(title).toHaveFocus()
    expect(title.querySelector('time')).toHaveAttribute('datetime')
    // Not an input error: nothing red, nothing marked invalid.
    expect(view.container.querySelector('.fr-message--error, [aria-invalid]')).toBeNull()

    await fireEvent.click(view.getByRole('button', { name: 'Découvrir les modèles' }))
    expect(comparator.reveal).toHaveBeenCalled()
    comparator.pause = undefined
  })
})
