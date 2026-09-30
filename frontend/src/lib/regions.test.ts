import { describe, expect, it } from 'vitest'
import { formatRegion } from './regions'

describe('formatRegion', () => {
  it('localizes a country and derives its flag', () => {
    expect(formatRegion('us', 'fr')).toEqual({ code: 'US', flag: '🇺🇸', name: 'États-Unis' })
  })

  it('supports supranational ISO region codes', () => {
    expect(formatRegion('EU', 'fr')).toEqual({
      code: 'EU',
      flag: '🇪🇺',
      name: 'Union européenne'
    })
  })
})
