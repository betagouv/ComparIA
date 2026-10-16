import { clockTime } from '$lib/clockTime'
import { m } from '$lib/i18n/messages'
import { getLocale } from '$lib/i18n/runtime'

/** Stands for the clock time in a sentence, so the time can sit in a <time>. */
export const TIME_SLOT = '\u2063'

export interface ResetTime {
  datetime?: string | null
  clock?: ReturnType<typeof clockTime>
  /** "jusqu'à 15 h 40", "jusqu'à demain à 1 h 30", or "pour moins de deux heures". */
  until: string
}

export function resetTime(resetsAt: string | null | undefined): ResetTime {
  const clock = resetsAt ? clockTime(new Date(resetsAt), getLocale()) : undefined
  const until = !clock
    ? m['arene.limits.time.untilSoon']()
    : m[clock.tomorrow ? 'arene.limits.time.untilTomorrow' : 'arene.limits.time.until']({
        time: TIME_SLOT
      })
  return { datetime: resetsAt, clock, until }
}

/** "Vous pourrez écrire à nouveau à 15 h 40", with TIME_SLOT where the time goes. */
export function pauseTitle(reset: ResetTime): string {
  if (!reset.clock) return m['arene.limits.pause.titleSoon']()
  return m[reset.clock.tomorrow ? 'arene.limits.pause.titleTomorrow' : 'arene.limits.pause.title']({
    time: TIME_SLOT
  })
}

/** The sentence as a screen reader hears it, the time in place. */
export function spoken(text: string, reset: ResetTime): string {
  return text.replace(TIME_SLOT, reset.clock?.time ?? '')
}
