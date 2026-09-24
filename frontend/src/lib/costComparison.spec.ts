import { describe, expect, it } from 'vitest'
import { buildCostComparison } from './costComparison'

describe('buildCostComparison', () => {
  it('compares a model that costs more or less than the other', () => {
    expect(buildCostComparison(0.00006, 0.00004)).toEqual({ kind: 'more', factor: 1.5 })
    expect(buildCostComparison(0.00004, 0.00006)).toEqual({ kind: 'less', factor: 1.5 })
  })

  it('recognizes similar costs', () => {
    expect(buildCostComparison(0.00004, 0.00004)).toEqual({ kind: 'similar' })
    expect(buildCostComparison(0.000043, 0.00004)).toEqual({ kind: 'similar' })
  })

  it('handles free and unavailable comparisons without an infinite percentage', () => {
    expect(buildCostComparison(0, 0.00004)).toEqual({ kind: 'unavailable' })
    expect(buildCostComparison(0.00004, 0)).toEqual({ kind: 'unavailable' })
    expect(buildCostComparison(Number.NaN, 0.00004)).toEqual({ kind: 'unavailable' })
  })
})
