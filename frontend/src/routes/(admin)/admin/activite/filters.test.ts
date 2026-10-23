import { describe, expect, it } from 'vitest'
import { journeyChanges, journeyOf, nextQuery } from './filters'

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
