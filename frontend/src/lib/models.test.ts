import { describe, expect, it } from 'vitest'

import { assignRankClasses, MAX_RANK_CLASS, rankClassSpans } from './models'

/** A model is only its two confidence bounds as far as class assignment cares. */
const ci = (low: number, high: number) => ({ score_p2_5: low, score_p97_5: high })

describe('assignRankClasses', () => {
  it('puts a lone model in class 1', () => {
    expect(assignRankClasses([ci(990, 1010)])).toEqual([1])
  })

  it('handles an empty list', () => {
    expect(assignRankClasses([])).toEqual([])
  })

  it('keeps models whose intervals all reach the leader in one class', () => {
    expect(assignRankClasses([ci(990, 1010), ci(985, 1005), ci(980, 1000)])).toEqual([1, 1, 1])
  })

  it('splits models whose intervals never touch', () => {
    expect(assignRankClasses([ci(990, 1010), ci(950, 970), ci(910, 930)])).toEqual([1, 2, 3])
  })

  it('does not let the anchor drift down a chain of overlaps', () => {
    // B overlaps A, C overlaps B, but C is clearly below A. A drifting anchor
    // would chain all three into one class; the fixed anchor splits at C.
    expect(assignRankClasses([ci(990, 1010), ci(970, 995), ci(950, 975)])).toEqual([1, 1, 2])
  })

  it('stops splitting at the cap and puts the remainder in the last class', () => {
    // Ten models, none overlapping: without the cap this would be 1..10.
    const models = Array.from({ length: 10 }, (_, i) => ci(1000 - i * 100, 1010 - i * 100))
    expect(assignRankClasses(models)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 8, 8])
    expect(MAX_RANK_CLASS).toBe(8)
  })
})

describe('rankClassSpans', () => {
  it('reports the first and last rank of each class', () => {
    expect(
      rankClassSpans([
        { rank: 1, rankClass: '1' },
        { rank: 2, rankClass: '1' },
        { rank: 3, rankClass: '2' }
      ])
    ).toEqual({ '1': { min: 1, max: 2 }, '2': { min: 3, max: 3 } })
  })

  it('does not depend on the models arriving in rank order', () => {
    expect(
      rankClassSpans([
        { rank: 3, rankClass: '2' },
        { rank: 1, rankClass: '1' },
        { rank: 2, rankClass: '1' }
      ])
    ).toEqual({ '1': { min: 1, max: 2 }, '2': { min: 3, max: 3 } })
  })
})
