import { expectAccessible } from '$lib/testing/a11y'
import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PriceGraph from './PriceGraph.svelte'

const model = (
  id: string,
  price_out: number,
  elo: number,
  kind: 'open-source' | 'open-weights' | 'proprietary' = 'open-weights'
) => ({
  id,
  human_id: id,
  search: id,
  price_in: price_out / 4,
  price_out,
  status: 'enabled',
  license: { kind },
  lab: { name: 'Test Lab', logo: null },
  badges: { license: { text: kind } },
  data: { elo, rank: 1, rankClass: '1' }
})

vi.mock('$lib/models', () => ({
  applyStyleControl: (models: unknown[]) => models,
  getModelsWithDataContext: () => ({
    commons: { currency: { code: 'EUR', rate_from_usd: 1 } },
    models: [
      model('cheap-weak', 0.1, 1000),
      model('dominated', 5, 1050, 'proprietary'),
      model('mid', 1, 1100, 'open-source'),
      model('pricey-best', 10, 1200, 'proprietary')
    ]
  })
}))

describe('PriceGraph', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('draws the frontier through the undominated models only', () => {
    const { container } = render(PriceGraph)

    const frontier = container.querySelectorAll('svg circle.frontier')
    expect(frontier).toHaveLength(3)
    expect(container.querySelectorAll('svg circle')).toHaveLength(4)

    // Three models plus the flat run to each edge of the chart.
    const line = container.querySelector('svg polyline.frontier')!
    expect(line.getAttribute('points')!.split(' ')).toHaveLength(5)

    const labels = [...container.querySelectorAll('svg text.label')].map((t) => t.textContent)
    expect(labels).toEqual(['cheap-weak', 'mid', 'pricey-best'])
  })

  it('keeps both axes when the search matches nothing', async () => {
    const { container } = render(PriceGraph)

    const search = container.querySelector<HTMLInputElement>('#price-graph-model-search-desktop')!
    await fireEvent.input(search, { target: { value: 'no such model' } })

    expect(container.querySelectorAll('svg circle')).toHaveLength(0)
    expect(container.querySelectorAll('svg .x-axis text').length).toBeGreaterThanOrEqual(2)
    expect(container.querySelectorAll('svg .y-axis text').length).toBeGreaterThanOrEqual(2)
    expect(container.querySelector('svg')!.innerHTML).not.toContain('NaN')
  })

  it('names itself and mirrors the licence ramp in the legend', async () => {
    const { container } = render(PriceGraph)

    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('role')).toBe('img')
    expect(svg.getAttribute('aria-label')).toContain('Bradley-Terry')
    const title = container.querySelector(`#${svg.getAttribute('aria-describedby')}`)!
    expect(title.tagName.toLowerCase()).toBe('desc')

    await expectAccessible(container)
  })
})
