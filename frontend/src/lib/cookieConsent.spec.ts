import { describe, expect, it } from 'vitest'
import { decideCookieConsent, parseCookieConsent, serializeCookieConsent } from './cookieConsent'

const now = new Date('2026-11-25T12:00:00Z')
const givenAt = new Date('2026-10-01T12:00:00Z')
const seconds = (date: Date) => Math.floor(date.getTime() / 1000)

describe('cookie consent value', () => {
  it('writes a value made of digits and dots only', () => {
    expect(serializeCookieConsent({ measurement: true }, givenAt)).toBe(`1.1.${seconds(givenAt)}`)
  })

  it('reads back what it wrote', () => {
    const value = serializeCookieConsent({ measurement: false }, givenAt)
    expect(parseCookieConsent(value, now)).toEqual({ measurement: false, givenAt })
  })

  it.each([undefined, null, '', 'yes', '1.1', '1.2.1790000000', '1.1.abc', '1.1.-5'])(
    'treats %s as not asked',
    (value) => {
      expect(parseCookieConsent(value, now)).toBeNull()
    }
  )

  it('treats an older version as not asked', () => {
    expect(parseCookieConsent(`0.1.${seconds(givenAt)}`, now)).toBeNull()
  })

  it('treats a value written before the banner asked one question as not asked', () => {
    expect(parseCookieConsent(`1.1.1.${seconds(givenAt)}`, now)).toBeNull()
  })

  it('keeps a choice until six months have passed', () => {
    const value = `1.1.${seconds(new Date('2026-05-28T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).not.toBeNull()
  })

  it('treats a choice older than six months as not asked', () => {
    const value = `1.1.${seconds(new Date('2026-05-27T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).toBeNull()
  })

  it('treats a date too large to read as not asked', () => {
    expect(parseCookieConsent(`1.1.${'9'.repeat(400)}`, now)).toBeNull()
  })

  it('treats a choice dated in the future as not asked', () => {
    const value = `1.1.${seconds(new Date('2026-11-27T12:00:00Z'))}`
    expect(parseCookieConsent(value, now)).toBeNull()
  })

  it('allows a clock a few hours ahead', () => {
    const value = `1.1.${seconds(new Date('2026-11-25T18:00:00Z'))}`
    expect(parseCookieConsent(value, now)).not.toBeNull()
  })
})

describe('decideCookieConsent', () => {
  const answer = (measurement: boolean) => serializeCookieConsent({ measurement }, givenAt)
  const measured = (switchOn: boolean | null) => ({ switchOn, measured: true })

  it.each([true, false, null])(
    'neither asks nor measures when nothing is measured, with the switch %s',
    (switchOn) => {
      for (const value of [undefined, answer(true)]) {
        expect(decideCookieConsent({ switchOn, measured: false }, value, now)).toEqual({
          showBanner: false,
          loadMeasurement: false
        })
      }
    }
  )

  it('changes nothing when the switch is off, whatever the cookie says', () => {
    for (const value of [undefined, answer(false)]) {
      expect(decideCookieConsent(measured(false), value, now)).toEqual({
        showBanner: false,
        loadMeasurement: true
      })
    }
  })

  it('holds Matomo back without asking when the switch is unknown', () => {
    for (const value of [undefined, answer(true)]) {
      expect(decideCookieConsent(measured(null), value, now)).toEqual({
        showBanner: false,
        loadMeasurement: false
      })
    }
  })

  it('asks and holds Matomo back when nobody has answered', () => {
    expect(decideCookieConsent(measured(true), undefined, now)).toEqual({
      showBanner: true,
      loadMeasurement: false
    })
  })

  it('asks again when the cookie is unreadable', () => {
    expect(decideCookieConsent(measured(true), 'garbage', now).showBanner).toBe(true)
  })

  it.each([true, false])('follows an answer of %s', (measurement) => {
    expect(decideCookieConsent(measured(true), answer(measurement), now)).toEqual({
      showBanner: false,
      loadMeasurement: measurement
    })
  })
})
