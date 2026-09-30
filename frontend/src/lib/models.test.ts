import { describe, expect, it } from 'vitest'

import type { PersonalRankingRow } from '$lib/generated/backend'
import {
  assignRankClasses,
  isModelNew,
  joinPersonalRanking,
  MAX_RANK_CLASS,
  rankClassSpans,
  type BotModel
} from './models'

describe('isModelNew', () => {
  const today = new Date('2026-08-26T12:00:00Z')

  it.each([
    ['release day', '2026-08-26', true],
    ['same day in the following month', '2026-07-26', true],
    ['one day beyond the calendar month', '2026-07-25', false],
    ['a future release', '2026-08-27', false]
  ])('%s', (_label, releaseDate, expected) => {
    expect(isModelNew(releaseDate, today)).toBe(expected)
  })

  it('clamps month-end releases to the final day of the next month', () => {
    expect(isModelNew('2026-01-31', new Date('2026-02-28T23:59:59Z'))).toBe(true)
    expect(isModelNew('2026-01-31', new Date('2026-03-01T00:00:00Z'))).toBe(false)
  })
})

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

describe('joinPersonalRanking', () => {
  /** Only the fields the join reads. */
  const model = (id: string, human_id: string) =>
    ({ id, human_id, search: `${human_id} lab` }) as BotModel

  const personalRow = (llm_id: string, name: string, rank: number): PersonalRankingRow => ({
    llm_id,
    name,
    rank,
    score: 0.667,
    battles: 1,
    wins: 1,
    losses: 0,
    ties: 0
  })

  it('attaches the model and its place in the general ranking', () => {
    const [row] = joinPersonalRanking(
      [personalRow('a', 'Mistral Large', 1)],
      [model('a', 'mistral-large')],
      { a: 4 }
    )

    expect(row.model?.human_id).toBe('mistral-large')
    expect(row.generalRank).toBe(4)
    expect(row.search).toBe('mistral-large lab')
  })

  it('keeps a model that has left the arena, under the name the server sent', () => {
    const [row] = joinPersonalRanking([personalRow('gone', 'Retired model', 1)], [], {})

    expect(row.model).toBeNull()
    expect(row.name).toBe('Retired model')
    expect(row.search).toBe('Retired model')
  })

  it('gives no general rank to a model the general ranking does not hold', () => {
    const [row] = joinPersonalRanking(
      [personalRow('a', 'Mistral Large', 1)],
      [model('a', 'mistral-large')],
      {}
    )

    expect(row.generalRank).toBeNull()
  })

  it('keeps the order the server sent', () => {
    const rows = joinPersonalRanking(
      [personalRow('b', 'B', 1), personalRow('a', 'A', 2)],
      [model('a', 'a'), model('b', 'b')],
      { a: 1, b: 2 }
    )

    expect(rows.map((row) => row.id)).toEqual(['b', 'a'])
  })
})
