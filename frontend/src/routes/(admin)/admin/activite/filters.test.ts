import { describe, expect, it } from 'vitest'
import { journeyChanges, journeyOf, modeKeys, modeLabel, nextQuery } from './filters'

describe('the journey filter', () => {
  it('lists the stopped messages through their flag', () => {
    const params = new URLSearchParams('period=7d&has_vote=true')
    const query = new URLSearchParams(nextQuery(params, journeyChanges('stopped', params)))

    expect(query.get('flag')).toBe('stopped')
    expect(query.get('has_vote')).toBeNull()
    expect(journeyOf(query)).toBe('stopped')
  })

  it('drops the stopped flag when going back to conversations, not another flag', () => {
    const stopped = new URLSearchParams('flag=stopped')
    const pii = new URLSearchParams('flag=pii')

    expect(
      new URLSearchParams(nextQuery(stopped, journeyChanges('voted', stopped))).get('flag')
    ).toBeNull()
    expect(new URLSearchParams(nextQuery(pii, journeyChanges('voted', pii))).get('flag')).toBe(
      'pii'
    )
  })
})

describe('modes', () => {
  const known = [
    { key: 'random', label: 'Aléatoire' },
    { key: 'legal', label: 'Juridique' }
  ]

  it('lists the modes of the instance first, then keys only comparisons still carry', () => {
    expect(modeKeys(known, { custom: 3, random: 10 })).toEqual(['random', 'legal', 'custom'])
  })

  it('names a mode by its label, and a deleted one by its key', () => {
    expect(modeLabel(known, 'legal')).toBe('Juridique')
    expect(modeLabel(known, 'custom')).toBe('custom')
  })
})
