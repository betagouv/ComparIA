import type { CurrencyInfo } from '$lib/generated/backend'
import { describe, expect, it } from 'vitest'
import { convertFromUsd, formatCurrencyFromUsd, formatUsageCostFromUsd } from './currency'

const currency = (code: string, rateFromUsd: number): CurrencyInfo => ({
  code,
  rate_from_usd: rateFromUsd,
  date: '2026-07-08',
  source: code === 'EUR' ? 'base' : 'frankfurter'
})

describe('currency formatting', () => {
  it.each([
    ['USD', 1, 10],
    ['EUR', 0.85, 8.5],
    ['DKK', 6.37, 63.7]
  ])('converts USD prices to %s', (code, rate, expected) => {
    expect(convertFromUsd(10, currency(code, rate))).toBeCloseTo(expected)
  })

  it('formats euros, US dollars and Danish kroner for their locales', () => {
    expect(formatCurrencyFromUsd(12.5, currency('EUR', 0.85), 'fr-FR')).toBe('10,63 EUR')
    expect(formatCurrencyFromUsd(12.5, currency('USD', 1), 'en-US')).toBe('USD 12.50')
    expect(formatCurrencyFromUsd(12.5, currency('DKK', 6.37), 'da-DK')).toBe('79,63 DKK')
  })

  it('keeps up to six decimals for small conversation costs', () => {
    expect(formatUsageCostFromUsd(0.0001, currency('EUR', 0.85), 'fr-FR')).toBe('0,000085 EUR')
    expect(formatUsageCostFromUsd(0.0001, currency('USD', 1), 'en-US')).toBe('USD 0.0001')
    expect(formatUsageCostFromUsd(0.0001, currency('DKK', 6.37), 'da-DK')).toBe('0,000637 DKK')
  })

  it('retains precision for currencies with different standard fraction digits', () => {
    expect(formatUsageCostFromUsd(0.0001, currency('JPY', 150), 'ja-JP')).toBe('JPY 0.015')
    expect(formatUsageCostFromUsd(0.0001, currency('BHD', 0.38), 'ar-BH')).toBe('‏٠٫٠٠٠٠٣٨ BHD')
  })

  it('shows a minimum unit only below six decimal places', () => {
    expect(formatUsageCostFromUsd(0.0000001, currency('USD', 1), 'en-US')).toBe('< USD 0.000001')
  })
})
