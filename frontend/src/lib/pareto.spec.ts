import { describe, expect, it } from 'vitest'
import { paretoFrontier } from './pareto'

describe('paretoFrontier', () => {
  it('is empty for no points', () => {
    expect(paretoFrontier([])).toEqual([])
  })

  it('keeps a lone point', () => {
    expect(paretoFrontier([{ id: 'a', x: 1, y: 1 }])).toEqual(['a'])
  })

  it('drops points beaten on both axes and orders the rest by price', () => {
    const points = [
      { id: 'pricey-best', x: 10, y: 1300 },
      { id: 'cheap-weak', x: 0.1, y: 1000 },
      { id: 'dominated', x: 5, y: 1100 },
      { id: 'mid', x: 1, y: 1200 }
    ]
    expect(paretoFrontier(points)).toEqual(['cheap-weak', 'mid', 'pricey-best'])
  })

  it('keeps only the stronger of two points at the same price', () => {
    const points = [
      { id: 'weak', x: 1, y: 1000 },
      { id: 'strong', x: 1, y: 1100 }
    ]
    expect(paretoFrontier(points)).toEqual(['strong'])
  })

  it('drops a pricier point that only ties the score', () => {
    const points = [
      { id: 'cheap', x: 1, y: 1000 },
      { id: 'pricier', x: 2, y: 1000 }
    ]
    expect(paretoFrontier(points)).toEqual(['cheap'])
  })
})
