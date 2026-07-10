import type { CurrencyInfo } from '$lib/generated/backend'
import { describe, expect, it } from 'vitest'
import { convertFromEuro, formatCurrencyFromEuro, formatUsageCostFromEuro } from './currency'

const currency = (code: string, rateFromEuro: number): CurrencyInfo => ({
  code,
  rate_from_eur: rateFromEuro,
  date: '2026-07-08',
  source: code === 'EUR' ? 'base' : 'frankfurter'
})

describe('currency formatting', () => {
  it.each([
    ['EUR', 1, 10],
    ['USD', 1.14, 11.4],
    ['DKK', 7.47, 74.7]
  ])('converts euro prices to %s', (code, rate, expected) => {
    expect(convertFromEuro(10, currency(code, rate))).toBeCloseTo(expected)
  })

  it('formats euros, US dollars and Danish kroner for their locales', () => {
    expect(formatCurrencyFromEuro(12.5, currency('EUR', 1), 'fr-FR')).toBe('12,50 EUR')
    expect(formatCurrencyFromEuro(12.5, currency('USD', 1.14), 'en-US')).toBe('USD 14.25')
    expect(formatCurrencyFromEuro(12.5, currency('DKK', 7.47), 'da-DK')).toBe('93,38 DKK')
  })

  it('shows the smallest monetary unit for tiny conversation costs', () => {
    expect(formatUsageCostFromEuro(0.0001, currency('EUR', 1), 'fr-FR')).toBe('< 0,01 EUR')
    expect(formatUsageCostFromEuro(0.0001, currency('USD', 1.14), 'en-US')).toBe('< USD 0.01')
    expect(formatUsageCostFromEuro(0.0001, currency('DKK', 7.47), 'da-DK')).toBe('< 0,01 DKK')
  })
})
