const LED_REFERENCE_WATTS = 6
const PHONE_BATTERY_REFERENCE_WH = 15
const VIDEO_STREAMING_REFERENCE_WATTS = 80

export interface EnergyEquivalences {
  ledDuration: string
  phoneBatteryPercentage: string
  videoDuration: string
}

function formatNumber(value: number, locale: string, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(value)
}

function formatLongDuration(
  value: number,
  unit: 'days' | 'weeks' | 'years',
  locale: string
): string {
  const units = {
    fr: { days: 'j', weeks: 'sem.', years: 'ans' },
    en: { days: 'd', weeks: 'wk', years: 'yr' },
    da: { days: 'd', weeks: 'uger', years: 'år' },
    sv: { days: 'd', weeks: 'veckor', years: 'år' },
    lt: { days: 'd.', weeks: 'sav.', years: 'm.' }
  } as const
  const language = locale.split('-')[0] as keyof typeof units
  const localizedUnits = units[language] ?? units.en

  return `${formatNumber(value, locale, 1)} ${localizedUnits[unit]}`
}

function formatDuration(seconds: number, locale: string): string {
  if (seconds < 0.5) return '< 1 s'
  if (seconds < 60) return `${formatNumber(Math.round(seconds), locale)} s`
  if (seconds < 600) return `${formatNumber(Math.round(seconds / 10) * 10, locale)} s`
  if (seconds < 3600) return `${formatNumber(Math.round(seconds / 60), locale)} min`

  if (seconds >= 365 * 24 * 3600) {
    return formatLongDuration(seconds / (365 * 24 * 3600), 'years', locale)
  }

  if (seconds >= 7 * 24 * 3600) {
    return formatLongDuration(seconds / (7 * 24 * 3600), 'weeks', locale)
  }

  if (seconds >= 24 * 3600) {
    return formatLongDuration(seconds / (24 * 3600), 'days', locale)
  }

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  if (minutes === 60) return `${formatNumber(hours + 1, locale)} h`
  return minutes === 0
    ? `${formatNumber(hours, locale)} h`
    : `${formatNumber(hours, locale)} h ${formatNumber(minutes, locale)} min`
}

function formatPhoneBatteryPercentage(percentage: number, locale: string): string {
  if (percentage < 0.1) return `< ${formatNumber(0.1, locale, 1)} %`
  if (percentage < 1) return `${formatNumber(percentage, locale, 1)} %`
  return `${formatNumber(percentage, locale)} %`
}

export function buildEnergyEquivalences(
  energyMwh: number,
  locale: string
): EnergyEquivalences | null {
  if (!Number.isFinite(energyMwh) || energyMwh <= 0) return null

  const ledSeconds = (energyMwh / 1000 / LED_REFERENCE_WATTS) * 3600
  const videoSeconds = (energyMwh / 1000 / VIDEO_STREAMING_REFERENCE_WATTS) * 3600
  const phoneBatteryPercentage = (energyMwh / (PHONE_BATTERY_REFERENCE_WH * 1000)) * 100

  return {
    ledDuration: formatDuration(ledSeconds, locale),
    phoneBatteryPercentage: formatPhoneBatteryPercentage(phoneBatteryPercentage, locale),
    videoDuration: formatDuration(videoSeconds, locale)
  }
}
