import type { CurrencyInfo } from '$lib/generated/backend'

function currencyFormatter(currency: CurrencyInfo, locale: string): Intl.NumberFormat {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency.code,
    currencyDisplay: 'code'
  })
}

export function convertFromUsd(amount: number, currency: CurrencyInfo): number {
  return amount * currency.rate_from_usd
}

export function formatCurrencyFromUsd(
  amount: number,
  currency: CurrencyInfo,
  locale: string
): string {
  return currencyFormatter(currency, locale).format(convertFromUsd(amount, currency))
}

export function formatUsageCostFromUsd(
  amount: number,
  currency: CurrencyInfo,
  locale: string
): string {
  const converted = convertFromUsd(amount, currency)
  const maximumFractionDigits = 6
  const minimumUnit = 10 ** -maximumFractionDigits
  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency.code,
    currencyDisplay: 'code',
    minimumFractionDigits: 2,
    maximumFractionDigits
  })

  if (converted > 0 && converted < minimumUnit) {
    return `< ${formatter.format(minimumUnit)}`
  }
  return formatter.format(converted)
}
