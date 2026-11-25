import { COOKIE_CONSENT_NAME, serializeCookieConsent } from '$lib/cookieConsent'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createCookieConsent } from './cookieConsent.svelte'

const now = new Date('2026-11-25T12:00:00Z')

function setCookie(value: string) {
  document.cookie = `${COOKIE_CONSENT_NAME}=${value}; path=/`
}

function readCookie() {
  return document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(`${COOKIE_CONSENT_NAME}=`))
    ?.split('=')[1]
}

function create(enabled: boolean | null = true) {
  const consent = createCookieConsent({ enabled: () => enabled, now: () => now })
  consent.load()
  return consent
}

describe('cookie consent store', () => {
  afterEach(() => {
    document.cookie = `${COOKIE_CONSENT_NAME}=; path=/; max-age=0`
  })

  it('keeps the banner closed until it has read the cookie', () => {
    const consent = createCookieConsent({ enabled: () => true, now: () => now })
    expect(consent.bannerOpen).toBe(false)
    consent.load()
    expect(consent.bannerOpen).toBe(true)
  })

  it('knows an earlier answer before the banner is allowed to open', () => {
    setCookie(serializeCookieConsent({ measurement: true, preferences: true }, now))
    const consent = createCookieConsent({ enabled: () => true, now: () => now })
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.keepSettings).toBe(true)
  })

  it('tells whether the switch is on', () => {
    expect(create(true).enabled).toBe(true)
    expect(create(false).enabled).toBe(false)
  })

  it('stays closed and offers no reopening while the switch is unknown', () => {
    const consent = create(null)
    expect(consent.enabled).toBe(false)
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(false)
  })

  it('opens the banner when nobody has answered', () => {
    const consent = create()
    expect(consent.bannerOpen).toBe(true)
    expect(consent.choice).toBeNull()
    expect(consent.decision).toEqual({
      showBanner: true,
      loadMeasurement: false,
      keepSettings: false
    })
  })

  it('reads an earlier answer from the cookie', () => {
    setCookie(serializeCookieConsent({ measurement: true, preferences: false }, now))
    const consent = create()
    expect(consent.bannerOpen).toBe(false)
    expect(consent.choice).toEqual({ measurement: true, preferences: false })
  })

  it('writes the answer, closes the banner and tells subscribers', () => {
    const consent = create()
    const listener = vi.fn()
    consent.onChange(listener)

    consent.save({ measurement: false, preferences: true })

    expect(readCookie()).toBe(
      serializeCookieConsent({ measurement: false, preferences: true }, now)
    )
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.keepSettings).toBe(true)
    expect(listener).toHaveBeenCalledWith({ measurement: false, preferences: true }, null)
  })

  it('stops telling a subscriber once it unsubscribes', () => {
    const consent = create()
    const listener = vi.fn()
    consent.onChange(listener)()
    consent.save({ measurement: true, preferences: true })
    expect(listener).not.toHaveBeenCalled()
  })

  it('reopens the banner on demand and closes it again', () => {
    setCookie(serializeCookieConsent({ measurement: true, preferences: true }, now))
    const consent = create()
    consent.reopen()
    expect(consent.bannerOpen).toBe(true)
    consent.close()
    expect(consent.bannerOpen).toBe(false)
  })

  it('gives focus back to whatever reopened the banner', () => {
    setCookie(serializeCookieConsent({ measurement: true, preferences: true }, now))
    const consent = create()
    const link = document.body.appendChild(document.createElement('button'))
    link.focus()

    consent.reopen()
    link.blur()
    consent.save({ measurement: false, preferences: true })

    expect(link).toHaveFocus()
    link.remove()
  })

  it('never opens when the switch is off', () => {
    const consent = create(false)
    consent.reopen()
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision).toEqual({
      showBanner: false,
      loadMeasurement: true,
      keepSettings: true
    })
  })
})
