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

function create(enabled: boolean | null = true, measured = true, hasText = true) {
  const consent = createCookieConsent({
    enabled: () => enabled,
    measured: () => measured,
    hasText: () => hasText,
    now: () => now
  })
  consent.load()
  return consent
}

describe('cookie consent store', () => {
  afterEach(() => {
    document.cookie = `${COOKIE_CONSENT_NAME}=; path=/; max-age=0`
  })

  it('keeps the banner closed until it has read the cookie', () => {
    const consent = createCookieConsent({
      enabled: () => true,
      measured: () => true,
      hasText: () => true,
      now: () => now
    })
    expect(consent.bannerOpen).toBe(false)
    consent.load()
    expect(consent.bannerOpen).toBe(true)
  })

  it('knows an earlier answer before the banner is allowed to open', () => {
    setCookie(serializeCookieConsent({ measurement: true }, now))
    const consent = createCookieConsent({
      enabled: () => true,
      measured: () => true,
      hasText: () => true,
      now: () => now
    })
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(true)
  })

  it('asks only when the switch is on', () => {
    expect(create(true).asking).toBe(true)
    expect(create(false).asking).toBe(false)
  })

  it('stays closed and offers no reopening when nothing is measured', () => {
    const consent = create(true, false)
    expect(consent.asking).toBe(false)
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(false)
  })

  it('stays closed and offers no reopening while the switch is unknown', () => {
    const consent = create(null)
    expect(consent.asking).toBe(false)
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(false)
  })

  it('offers no reopening when the banner text could not be loaded', () => {
    setCookie(serializeCookieConsent({ measurement: true }, now))
    const consent = create(true, true, false)
    expect(consent.asking).toBe(false)
    consent.reopen()
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(true)
  })

  it('opens the banner when nobody has answered', () => {
    const consent = create()
    expect(consent.bannerOpen).toBe(true)
    expect(consent.choice).toBeNull()
    expect(consent.decision).toEqual({
      showBanner: true,
      loadMeasurement: false
    })
  })

  it('reads an earlier answer from the cookie', () => {
    setCookie(serializeCookieConsent({ measurement: true }, now))
    const consent = create()
    expect(consent.bannerOpen).toBe(false)
    expect(consent.choice).toEqual({ measurement: true })
  })

  it('writes the answer, closes the banner and tells subscribers', () => {
    const consent = create()
    const listener = vi.fn()
    consent.onChange(listener)

    consent.save({ measurement: false })

    expect(readCookie()).toBe(serializeCookieConsent({ measurement: false }, now))
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision.loadMeasurement).toBe(false)
    expect(listener).toHaveBeenCalledWith({ measurement: false }, null)
  })

  it('stops telling a subscriber once it unsubscribes', () => {
    const consent = create()
    const listener = vi.fn()
    consent.onChange(listener)()
    consent.save({ measurement: true })
    expect(listener).not.toHaveBeenCalled()
  })

  it('reopens the banner on demand and closes it again', () => {
    setCookie(serializeCookieConsent({ measurement: true }, now))
    const consent = create()
    consent.reopen()
    expect(consent.bannerOpen).toBe(true)
    consent.close()
    expect(consent.bannerOpen).toBe(false)
  })

  it('gives focus back to whatever reopened the banner', () => {
    setCookie(serializeCookieConsent({ measurement: true }, now))
    const consent = create()
    const link = document.body.appendChild(document.createElement('button'))
    link.focus()

    consent.reopen()
    link.blur()
    consent.save({ measurement: false })

    expect(link).toHaveFocus()
    link.remove()
  })

  it('never opens when the switch is off', () => {
    const consent = create(false)
    consent.reopen()
    expect(consent.bannerOpen).toBe(false)
    expect(consent.decision).toEqual({
      showBanner: false,
      loadMeasurement: true
    })
  })
})
