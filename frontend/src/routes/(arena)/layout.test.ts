import { describe, expect, it, vi } from 'vitest'
import { load } from './+layout'

const queryLimits = vi.hoisted(() => vi.fn())

vi.mock('$lib/chatService.svelte', () => ({ queryComparisons: async () => [] }))
vi.mock('$lib/limits.svelte', () => ({ queryLimits }))

describe('the arena layout load', () => {
  it('never waits on the limits, so the page hydrates however long they take', async () => {
    const data = await (load as (event: unknown) => Promise<Record<string, unknown>>)({
      data: {},
      fetch
    })

    expect(queryLimits).not.toHaveBeenCalled()
    expect(data).toEqual({ comparisons: [] })
  })
})
