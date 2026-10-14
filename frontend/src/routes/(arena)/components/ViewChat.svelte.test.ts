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
  pauseFromSend: false,
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

vi.mock('$lib/voteTags', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/voteTags')>()),
  getVoteTagsContext: () => []
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
    comparator.pauseFromSend = true
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
    Object.assign(comparator, { pause: undefined, pauseFromSend: false })
  })

  it('tells a pause that shows after a turn without moving focus', () => {
    comparator.pause = {
      detail: 'allowance_spent',
      limit: { scope: 'network', resets_at: null, resets_in: null, llm_ids: [] }
    }
    const view = render(ViewChat, props)

    const title = view.getByRole('heading', { name: 'Pause de moins de deux heures' })
    expect(title).not.toHaveFocus()
    expect(view.getAllByRole('status')[0]).toHaveTextContent('Pause de moins de deux heures')
    comparator.pause = undefined
  })

  it('offers a new discussion, not the reveal, when the paused conversation failed', () => {
    comparator.pause = {
      detail: 'allowance_spent',
      limit: { scope: 'session', resets_at: null, resets_in: null, llm_ids: [] }
    }
    Object.assign(comparator, { error: 'provider_error', canReveal: false })
    const view = render(ViewChat, props)

    expect(view.getByRole('link', { name: 'Nouvelle discussion' })).toHaveAttribute('href', '/')
    expect(view.queryByRole('button', { name: 'Découvrir les modèles' })).toBeNull()
    expect(view.queryByText(/En attendant/)).toBeNull()
    Object.assign(comparator, { pause: undefined, error: undefined, canReveal: true })
  })

  describe('near the turn cap', () => {
    // The turns scroll into view as they show, and jsdom has no layout.
    Element.prototype.scrollIntoView ??= () => {}

    function turns(count: number) {
      return Array.from({ length: count }, (_, i) => ({
        id: `turn-${i}`,
        status: 'complete',
        choice: 'a_better',
        user_msg: { content: `Question ${i}` },
        a: {
          status: 'complete',
          llm_msg: { content: 'A' },
          keyword_annotations: [],
          custom_annotation: ''
        },
        b: {
          status: 'complete',
          llm_msg: { content: 'B' },
          keyword_annotations: [],
          custom_annotation: ''
        }
      }))
    }
    const comparison = comparator.comparison

    it.each([
      [17, null],
      [18, 'Encore 2 messages possibles dans cette conversation.'],
      [19, 'Dernier message possible dans cette conversation.']
    ])('after turn %i says how many are left, under the text box', (count, hint) => {
      comparator.comparison = { ...comparison, turns: turns(count) as never[] }
      const view = render(ViewChat, props)

      const box = view.container.querySelector('#chatbot-prompt')
      if (hint) {
        expect(box).toHaveAccessibleDescription(hint)
        // A hint, not an input error.
        expect(view.container.querySelector('.fr-message--error, [aria-invalid]')).toBeNull()
      } else {
        expect(box).toHaveAccessibleDescription('')
      }
      comparator.comparison = comparison
    })

    it('puts the full panel in place of the text box at turn 20', async () => {
      comparator.comparison = { ...comparison, turns: turns(20) as never[] }
      const view = render(ViewChat, props)

      expect(view.container.querySelector('#chatbot-prompt')).toBeNull()
      expect(
        view.getByRole('heading', { name: 'Cette conversation est complète' })
      ).not.toHaveFocus()
      expect(view.getByText(/au plus 20 messages/)).toBeInTheDocument()
      expect(view.getByRole('link', { name: 'Nouvelle discussion' })).toHaveAttribute('href', '/')
      expect(view.queryByRole('button', { name: revealLabel })).toBeNull()
      await fireEvent.click(view.getByRole('button', { name: 'Découvrir les modèles' }))
      expect(comparator.reveal).toHaveBeenCalled()
      comparator.comparison = comparison
    })
  })
})
