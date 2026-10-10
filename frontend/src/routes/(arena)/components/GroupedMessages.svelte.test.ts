import type { ComparisonTurn } from '$lib/chatService.svelte'
import { render } from '@testing-library/svelte'
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
  children: undefined
}

describe('GroupedMessages on a stopped turn', () => {
  it('shows the notice, the vote and Retry, and leaves focus alone', async () => {
    const { container } = render(GroupedMessages, { ...props, turn: turn('interrupted') })
    await tick()

    expect(container.querySelector('p[role="status"]')?.textContent).toContain('arrêtée')
    expect(container.querySelector('fieldset[id^=vote-select]')).not.toBeNull()
    expect(container.querySelector('button[id^=retry-]')).not.toBeNull()
    // The stop lives in the prompt bar now; a stopped turn loaded from
    // history must not steal focus.
    expect(document.activeElement).toBe(document.body)
  })

  it('renders no stop control of its own while generating', () => {
    const { container } = render(GroupedMessages, { ...props, turn: turn('generating') })
    expect(container.querySelector('button[id^=stop-]')).toBeNull()
    expect(container.querySelector('fieldset[id^=vote-select]')).toBeNull()
  })
})
