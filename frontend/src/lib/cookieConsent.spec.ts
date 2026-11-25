import { describe, expect, it } from 'vitest'
import { decideCookieConsent, parseCookieConsent, serializeCookieConsent } from './cookieConsent'

const now = new Date('2026-11-25T12:00:00Z')
const givenAt = new Date('2026-10-01T12:00:00Z')
const seconds = (date: Date) => Math.floor(date.getTime() / 1000)

describe('cookie consent value', () => {
  it('writes a value made of digits and dots only', () => {
    expect(serializeCookieConsent({ measurement: true, preferences: false }, givenAt)).toBe(
      `1.1.0.${seconds(givenAt)}`
    )
  })

  it('reads back what it wrote', () => {
    const value = serializeCookieConsent({ measurement: false, preferences: true }, givenAt)
    expect(parseCookieConsent(value, now)).toEqual({
      measurement: false,
      preferences: true,
      givenAt
    })
  })

  it.each([undefined, null, '', 'yes', '1.1.0', '1.2.0.1790000000', '1.1.0.abc', '1.1.0.-5'])(
    'treats %s as not asked',
    (value) => {
      expect(parseCookieConsent(value, now)).toBeNull()
    }
  )

  it('treats an older version as not asked', () => {
    expect(parseCookieConsent(`0.1.1.${seconds(givenAt)}`, now)).toBeNull()
  })

  it('keeps a choice until six months have passed', () => {
    const value = `1.1.1.${seconds(new Date('2026-05-28T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).not.toBeNull()
  })

  it('treats a choice older than six months as not asked', () => {
    const value = `1.1.1.${seconds(new Date('2026-05-27T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).toBeNull()
  })

  it('treats a date too large to read as not asked', () => {
    expect(parseCookieConsent(`1.1.1.${'9'.repeat(400)}`, now)).toBeNull()
  })

  it('treats a choice dated in the future as not asked', () => {
    const value = `1.1.1.${seconds(new Date('2026-11-27T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).toBeNull()
  })

  it('allows a clock a few hours ahead', () => {
    const value = `1.1.1.${seconds(new Date('2026-11-25T18:00:00Z'))}`
    expect(parseCookieConsent(value, now)).not.toBeNull()
  })
})

describe('decideCookieConsent', () => {
  const answer = (measurement: boolean, preferences: boolean) =>
    serializeCookieConsent({ measurement, preferences }, givenAt)

  it('changes nothing when the switch is off, whatever the cookie says', () => {
    for (const value of [undefined, answer(false, false)]) {
      expect(decideCookieConsent(false, value, now)).toEqual({
        showBanner: false,
        loadMeasurement: true,
        keepSettings: true
      })
    }
  })

  it('holds Matomo back without asking when the switch is unknown', () => {
    for (const value of [undefined, answer(true, true)]) {
      expect(decideCookieConsent(null, value, now)).toEqual({
        showBanner: false,
        loadMeasurement: false,
        keepSettings: true
      })
    }
  })

  it('asks and holds everything back when nobody has answered', () => {
    expect(decideCookieConsent(true, undefined, now)).toEqual({
      showBanner: true,
      loadMeasurement: false,
      keepSettings: false
    })
  })

  it('asks again when the cookie is unreadable', () => {
    expect(decideCookieConsent(true, 'garbage', now).showBanner).toBe(true)
  })

  it.each([
    [true, true],
    [true, false],
    [false, true],
    [false, false]
  ])('follows an answer of measurement %s and settings %s', (measurement, preferences) => {
    expect(decideCookieConsent(true, answer(measurement, preferences), now)).toEqual({
      showBanner: false,
      loadMeasurement: measurement,
      keepSettings: preferences
    })
  })
})
