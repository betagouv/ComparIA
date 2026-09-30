/**
 * The ranking charts need vote data the local stack does not have, so they are
 * covered here rather than in the browser suite. An SVG with no role and no
 * title is a blank rectangle to a screen reader, which is what both of these
 * were before the audit of 2026-08-13.
 */
import { render } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { expectAccessible, expectNoDuplicateIds } from '$lib/testing/a11y'
import EnergyGraph from './EnergyGraph.svelte'
import PriceGraph from './PriceGraph.svelte'
import WinHistogram from './WinHistogram.svelte'

const model = (id: string, kind: 'open-source' | 'proprietary') => ({
  id,
  human_id: id,
  search: id,
  price_in: 1,
  price_out: 4,
  consumption: 100,
  params: 8,
  active_params: null,
  size_class: 'XS',
  arch: 'dense',
  status: 'enabled',
  license: { kind },
  lab: { name: 'Test Lab', logo: null },
  badges: { license: { text: kind } },
  data: { elo: 1000, rank: 1, rankClass: '1' }
})

vi.mock('$lib/models', () => ({
  CONSO_SIZES: ['S', 'M', 'L'],
  applyStyleControl: (models: unknown[]) => models,
  getModelsWithDataContext: () => ({
    commons: { currency: { code: 'EUR', rate_from_usd: 1 } },
    models: [model('open', 'open-source'), model('closed', 'proprietary')]
  })
}))

describe('WinHistogram', () => {
  const data = [
    { x: 'Alpha', y: 0.62 },
    { x: 'Beta', y: 0.55 }
  ]

  it('names itself so it is not an anonymous graphic', async () => {
    const { container } = render(WinHistogram, {
      id: 'histogram-winrate',
      title: '10 premiers modèles selon le taux de victoire',
      data,
      minMaxY: [0, 1] as [number, number]
    })

    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('role')).toBe('img')

    const titleId = svg.getAttribute('aria-labelledby')!
    const title = container.querySelector(`#${titleId}`)!
    expect(title.tagName.toLowerCase()).toBe('title')
    expect(title.textContent).toContain('taux de victoire')

    await expectAccessible(container)
  })

  it('gives the two histograms on the methodology tab separate ids', () => {
    const { container: a } = render(WinHistogram, {
      id: 'histogram-winrate',
      title: 'Taux de victoire',
      data,
      minMaxY: [0, 1] as [number, number]
    })
    const { container: b } = render(WinHistogram, {
      id: 'histogram-elo',
      title: 'Bradley-Terry',
      data,
      minMaxY: [0, 1] as [number, number]
    })

    const ids = [a, b].map((c) => c.querySelector('svg')!.getAttribute('aria-labelledby'))
    expect(new Set(ids).size).toBe(2)
  })
})

describe('ranking graphs', () => {
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

  // Tabs keeps inactive panels mounted, so both graphs share the document. A
  // shared id sends the label of one graph's toggle to the other graph's input.
  it('keeps every id unique when both graphs are on the page', () => {
    render(EnergyGraph)
    render(PriceGraph)

    expectNoDuplicateIds(document.body)
  })
})
