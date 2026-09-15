import type { ComparisonTurn } from '$lib/chatService.svelte'
import { render, waitFor } from '@testing-library/svelte'
import { tick } from 'svelte'
import { describe, expect, it, vi } from 'vitest'
import GroupedMessages from './GroupedMessages.svelte'

// Reached through chatService, and it wants the runtime env at import time.
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))

function turn(status: ComparisonTurn['status'], sides = status): ComparisonTurn {
  const side = (content: string) => ({
    status: sides,
    llm_msg: { content, reasoning_content: '', interrupted: sides === 'interrupted' },
    keyword_annotations: [],
    custom_annotation: ''
  })
  return {
    id: 'turn-1',
    status,
    choice: null,
    user_msg: { content: 'Raconte une histoire', role: 'user', user_content: '' },
    a: side('Il était une fois'),
    b: side('Un jour')
  } as unknown as ComparisonTurn
}

const props = {
  disabled: false,
  onVote: vi.fn(),
  onRetry: vi.fn(),
  onStop: vi.fn(),
  children: undefined
}

/**
 * The Stop button unmounts with the 'interrupted' event, and a focused element
 * that unmounts drops focus to <body>. Same reasoning as the vote: hand it to
 * what the stop revealed.
 */
describe('GroupedMessages after a stop', () => {
  it('hands focus to the first vote choice once the turn is interrupted', async () => {
    const { container, rerender } = render(GroupedMessages, { ...props, turn: turn('generating') })

    const stop = container.querySelector<HTMLButtonElement>('button[id^=stop-]')!
    expect(stop).not.toBeNull()
    stop.focus()
    stop.click()
    expect(props.onStop).toHaveBeenCalledOnce()

    await rerender({ ...props, turn: turn('interrupted') })

    const firstChoice = container.querySelector('fieldset[id^=vote-select] button')
    expect(firstChoice).not.toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(firstChoice))
    expect(container.querySelector('p[role="status"]')?.textContent).toContain('arrêtée')
  })

  it('hands focus to Retry when the stop came before a first word', async () => {
    const { container, rerender } = render(GroupedMessages, { ...props, turn: turn('pending') })

    const stop = container.querySelector<HTMLButtonElement>('button[id^=stop-]')!
    stop.focus()
    stop.click()

    // Nothing was saved for a side that had not answered: the turn shows as
    // failed, the way a reload would show it.
    await rerender({ ...props, error: 'interrupted', turn: turn('error') })

    const retry = container.querySelector('[role="alert"] button')
    expect(retry).not.toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(retry))
  })

  it('offers Stop again on a retry after a stop', async () => {
    const { container, rerender } = render(GroupedMessages, { ...props, turn: turn('generating') })

    const stop = () => container.querySelector<HTMLButtonElement>('button[id^=stop-]')!
    stop().click()
    await tick()
    expect(stop().getAttribute('aria-disabled')).toBe('true')
    stop().click()
    expect(props.onStop).toHaveBeenCalledOnce()

    await rerender({ ...props, error: 'interrupted', turn: turn('error') })
    await rerender({ ...props, turn: turn('generating') })
    expect(stop().getAttribute('aria-disabled')).toBe('false')
  })

  it('leaves focus alone for a stopped turn that was not stopped from here', async () => {
    const { container } = render(GroupedMessages, { ...props, turn: turn('interrupted') })
    await tick()

    expect(container.querySelector('fieldset[id^=vote-select]')).not.toBeNull()
    expect(document.activeElement).toBe(document.body)
  })

  it('shows the button while generating and no longer once the turn is answered', async () => {
    const { container, rerender } = render(GroupedMessages, { ...props, turn: turn('generating') })
    expect(container.querySelector('button[id^=stop-]')).not.toBeNull()

    await rerender({ ...props, turn: turn('complete') })
    expect(container.querySelector('button[id^=stop-]')).toBeNull()
    expect(container.querySelector('fieldset[id^=vote-select]')).not.toBeNull()
  })
})
