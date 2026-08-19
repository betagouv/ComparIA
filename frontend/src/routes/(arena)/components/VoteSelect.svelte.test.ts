import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import VoteSelect from './VoteSelect.svelte'

// Reached through chatService, and it wants the runtime env at import time.
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))

/**
 * The desktop order has slipped once already, so it is pinned here. jsdom does
 * not apply the breakpoint, so both grids render and each is found by the class
 * that shows it.
 */
describe('VoteSelect', () => {
  const orderOf = (grid: Element) =>
    [...grid.querySelectorAll('button')].map((b) => b.dataset.choice)

  it('puts A and B at the ends on desktop and pairs them on the first row on mobile', () => {
    const { container } = render(VoteSelect, { id: 'vote-select-1', onVote: vi.fn() })
    const [mobile, desktop] = container.querySelectorAll('fieldset > div[class*="grid"]')

    expect(mobile.className).toContain('md:hidden')
    expect(orderOf(mobile)).toEqual(['a_better', 'b_better', 'both_bad', 'both_good'])

    expect(desktop.className).toContain('md:grid')
    expect(orderOf(desktop)).toEqual(['a_better', 'both_good', 'both_bad', 'b_better'])
  })
})
