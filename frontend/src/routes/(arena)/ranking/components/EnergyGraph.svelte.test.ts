import { render } from '@testing-library/svelte'
import { tick } from 'svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EnergyGraph from './EnergyGraph.svelte'

const observers: ResizeObserverCallback[] = []

vi.mock('$lib/models', () => ({
  CONSO_SIZES: ['S', 'M', 'L'],
  applyStyleControl: (models: unknown[]) => models,
  getModelsWithDataContext: () => ({
    models: [
      {
        id: 'test-model',
        search: 'test model',
        consumption: 100,
        params: 8,
        active_params: null,
        size_class: 'XS',
        arch: 'dense',
        status: 'enabled',
        license: { kind: 'open-source' },
        lab: { name: 'Test Lab', logo: null },
        data: {
          elo: 1000,
          rank: 1,
          rankClass: '1',
          score_p2_5: 990,
          score_p97_5: 1010
        }
      }
    ]
  })
}))

describe('EnergyGraph', () => {
  beforeEach(() => {
    observers.length = 0
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: ResizeObserverCallback) {
          observers.push(callback)
        }

        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('repositions data when its hidden tab becomes visible', async () => {
    const { container } = render(EnergyGraph)
    const circle = container.querySelector('svg circle')!
    const initialX = Number(circle.getAttribute('cx'))

    expect(observers).toHaveLength(1)

    observers[0](
      [
        {
          contentRect: { width: 0, height: 0 }
        } as ResizeObserverEntry
      ],
      {} as ResizeObserver
    )
    await tick()
    expect(Number(circle.getAttribute('cx'))).toBe(initialX)

    observers[0](
      [
        {
          contentRect: { width: 900, height: 700 }
        } as ResizeObserverEntry
      ],
      {} as ResizeObserver
    )
    await tick()

    const visibleX = Number(circle.getAttribute('cx'))
    expect(visibleX).not.toBe(initialX)
    expect(visibleX).toBeGreaterThan(72)
    expect(visibleX).toBeLessThan(900)
  })
})
