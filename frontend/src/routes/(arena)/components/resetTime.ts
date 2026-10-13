import { clockTime } from '$lib/clockTime'
import { m } from '$lib/i18n/messages'
import { getLocale } from '$lib/i18n/runtime'

/** Stands for the clock time in a sentence, so the time can sit in a <time>. */
export const TIME_SLOT = '\u2063'

export interface ResetTime {
  datetime?: string | null
  clock?: ReturnType<typeof clockTime>
  /** "à 15 h 40", "demain à 1 h 30", or "dans moins de deux heures" when unknown. */
  at: string
}

export function resetTime(resetsAt: string | null | undefined): ResetTime {
  const clock = resetsAt ? clockTime(new Date(resetsAt), getLocale()) : undefined
  const at = !clock
    ? m['arene.limits.time.within']()
    : m[clock.tomorrow ? 'arene.limits.time.tomorrowAt' : 'arene.limits.time.at']({
        time: TIME_SLOT
      })
  return { datetime: resetsAt, clock, at }
}
