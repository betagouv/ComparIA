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
  // No-break spaces throughout: "15 h" and "40", or "3:40" and "pm", must not
  // end up on two lines.
  const time =
    locale.split('-')[0] === 'fr'
      ? `${part('hour')}\u00a0h\u00a0${part('minute')}`
      : parts
          .map((p) => (p.type === 'dayPeriod' ? p.value.toLowerCase() : p.value))
          .join('')
          .replace(/\s/g, '\u00a0')
  return { time, tomorrow: at.toDateString() !== now.toDateString() }
}
