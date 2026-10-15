import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ViewChat from './ViewChat.svelte'

const comparator = vi.hoisted(() => ({
  comparison: { id: 'comparison-id', mode: 'random', revealed: false, turns: [] },
  comparisonId: 'comparison-id',
  status: 'complete',
  loading: false,
  error: undefined,
  canReveal: true,
  limitsRead: true,
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
const initial = { ...comparator }

// Here rather than at the end of each test, so one failed assertion does not
// leave its state to the next.
afterEach(() => {
  Object.assign(comparator, initial)
})
const revealLabel = 'Terminer et découvrir les modèles'

describe('ViewChat', () => {
  it('puts the pause notice in place of the text box and moves focus to its title', async () => {
    comparator.pauseFromSend = true
    comparator.pause = {
      scope: 'session',
      resets_at: new Date(Date.now() + 3600_000).toISOString(),
      resets_in: 3600
    }
    const view = render(ViewChat, props)

    expect(view.queryByRole('textbox')).toBeNull()
    const title = view.getByRole('heading', { name: /^Vous pourrez écrire à nouveau à/ })
    expect(title).toHaveFocus()
    expect(title.querySelector('time')).toHaveAttribute('datetime')
    // Not an input error: nothing red, nothing marked invalid.
    expect(view.container.querySelector('.fr-message--error, [aria-invalid]')).toBeNull()

    await fireEvent.click(view.getByRole('button', { name: revealLabel }))
    expect(comparator.reveal).toHaveBeenCalled()
    expect(view.getByRole('link', { name: 'Voir le classement' })).toHaveAttribute(
      'href',
      '/ranking'
    )
  })

  it('says why the pause in a toggletip under its buttons', async () => {
    comparator.pause = { scope: 'network', resets_at: null, resets_in: null }
    const view = render(ViewChat, props)
    const why = view.getByRole('button', { name: 'Pourquoi cette pause ?' })

    await fireEvent.click(why)

    expect(why).toHaveAttribute('aria-expanded', 'true')
    expect(document.getElementById('pause-notice-why')).toHaveTextContent(/tout le réseau/)
  })

  it('tells a pause that shows after a turn without moving focus', () => {
    comparator.pause = { scope: 'network', resets_at: null, resets_in: null }
    const view = render(ViewChat, props)

    const title = view.getByRole('heading', {
      name: 'Vous pourrez écrire à nouveau dans moins de deux heures'
    })
    expect(title).not.toHaveFocus()
    expect(view.getAllByRole('status')[0]).toHaveTextContent(
      'Vous pourrez écrire à nouveau dans moins de deux heures'
    )
  })

  it('offers a new discussion, not the reveal, when the paused conversation failed', () => {
    comparator.pause = { scope: 'session', resets_at: null, resets_in: null }
    Object.assign(comparator, { error: 'provider_error', canReveal: false })
    const view = render(ViewChat, props)

    expect(view.getByRole('link', { name: 'Nouvelle discussion' })).toHaveAttribute('href', '/')
    expect(view.queryByRole('button', { name: revealLabel })).toBeNull()
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
      // Shown: the limits are read.
      expect(box!.closest('.invisible')).toBeNull()
      if (hint) {
        expect(box).toHaveAccessibleDescription(hint)
        // A hint, not an input error.
        expect(view.container.querySelector('.fr-message--error, [aria-invalid]')).toBeNull()
      } else {
        expect(box).toHaveAccessibleDescription('')
      }
    })

    it('puts the full panel in place of the text box at turn 20', async () => {
      comparator.comparison = { ...comparison, turns: turns(20) as never[] }
      const view = render(ViewChat, props)

      expect(view.container.querySelector('#chatbot-prompt')).toBeNull()
      // Shown on load, not after a send from here: focus stays put.
      expect(view.getByRole('heading', { name: 'Conversation complète' })).not.toHaveFocus()
      expect(view.getByText(/au plus 20 messages/)).toBeInTheDocument()
      expect(view.container.querySelector('.fr-alert')).toBeNull()
      expect(view.getByRole('link', { name: 'Nouvelle discussion' })).toHaveAttribute('href', '/')
      // The card's own reveal button, not a second one under it.
      const reveal = view.getAllByRole('button', { name: revealLabel })
      expect(reveal).toHaveLength(1)
      await fireEvent.click(reveal[0])
      expect(comparator.reveal).toHaveBeenCalled()
    })
  })
})
