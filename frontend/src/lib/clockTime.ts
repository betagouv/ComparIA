/**
 * A time of day as people say it, in the browser's time zone: "15 h 40" in
 * French, "3:40 pm" in English. `tomorrow` is set when it falls after
 * midnight, for the copy to say so.
 */
export function clockTime(at: Date, locale: string, now = new Date()) {
  const parts = new Intl.DateTimeFormat(locale, {
    hour: 'numeric',
    minute: '2-digit'
  }).formatToParts(at)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value
  const time =
    locale.split('-')[0] === 'fr'
      ? `${part('hour')} h ${part('minute')}`
      : parts.map((p) => (p.type === 'dayPeriod' ? p.value.toLowerCase() : p.value)).join('')
  return { time, tomorrow: at.toDateString() !== now.toDateString() }
}
