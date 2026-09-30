import { describe, expect, it } from 'vitest'
import { buildEnergyEquivalences } from './energyEquivalences'

describe('buildEnergyEquivalences', () => {
  it('formats small values without displaying a misleading zero', () => {
    expect(buildEnergyEquivalences(14, 'fr-FR')).toEqual({
      ledDuration: '8 s',
      phoneBatteryPercentage: '< 0,1 %',
      videoDuration: '1 s'
    })
  })

  it('formats minutes, hours, and the phone battery percentage', () => {
    expect(buildEnergyEquivalences(1348, 'fr-FR')).toEqual({
      ledDuration: '13 min',
      phoneBatteryPercentage: '9 %',
      videoDuration: '60 s'
    })
    expect(buildEnergyEquivalences(13727, 'fr-FR')).toEqual({
      ledDuration: '2 h 17 min',
      phoneBatteryPercentage: '92 %',
      videoDuration: '10 min'
    })
  })

  it('uses the active locale for decimal separators', () => {
    expect(buildEnergyEquivalences(14, 'en-US')?.phoneBatteryPercentage).toBe('< 0.1 %')
  })

  it('uses larger time units for long-running equivalents', () => {
    expect(buildEnergyEquivalences(144_000, 'fr-FR')?.ledDuration).toBe('1 j')
    expect(buildEnergyEquivalences(2_016_000, 'fr-FR')?.ledDuration).toBe('2 sem.')
    expect(buildEnergyEquivalences(105_120_000, 'fr-FR')?.ledDuration).toBe('2 ans')
  })

  it.each([0, -1, Number.NaN, Number.POSITIVE_INFINITY])(
    'rejects invalid energy values: %s',
    (value) => {
      expect(buildEnergyEquivalences(value, 'fr-FR')).toBeNull()
    }
  )
})
