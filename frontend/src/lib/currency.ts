import type { CurrencyInfo } from '$lib/generated/backend'

function currencyFormatter(currency: CurrencyInfo, locale: string): Intl.NumberFormat {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency.code,
    currencyDisplay: 'code'
  })
}

export function convertFromEuro(amount: number, currency: CurrencyInfo): number {
  return amount * currency.rate_from_eur
}

export function formatCurrencyFromEuro(
  amount: number,
  currency: CurrencyInfo,
  locale: string
): string {
  return currencyFormatter(currency, locale).format(convertFromEuro(amount, currency))
}

export function formatUsageCostFromEuro(
  amount: number,
  currency: CurrencyInfo,
  locale: string
): string {
  const formatter = currencyFormatter(currency, locale)
  const converted = convertFromEuro(amount, currency)
  const fractionDigits = formatter.resolvedOptions().maximumFractionDigits
  const minimumUnit = 10 ** -fractionDigits

  if (converted > 0 && converted < minimumUnit) {
    return `< ${formatter.format(minimumUnit)}`
  }
  return formatter.format(converted)
}
