// @vitest-environment jsdom
import type { CookieChoice } from '$lib/cookieConsent'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { followMeasurementConsent } from './matomo'

type Listener = (choice: CookieChoice, previous: CookieChoice | null) => void

function fakeConsent() {
  let listener: Listener | null = null
  return {
    onChange(next: Listener) {
      listener = next
      return () => (listener = null)
    },
    answer(choice: Partial<CookieChoice>, previous: Partial<CookieChoice> | null = null) {
      listener?.({ measurement: false, ...choice }, previous && { measurement: false, ...previous })
    }
  }
}

function commands() {
  return (window._paq as unknown as unknown[][]).map((command) => command[0])
}

function matomoScripts() {
  return [...document.querySelectorAll('script')].filter((s) => s.src.endsWith('/matomo.js'))
}

// The server wrote the tracker into the page instead of the config element.
function serverLoadedMatomo() {
  document.body.innerHTML = ''
  window._paq = [['trackPageView']] as never
}

describe('audience measurement in the browser', () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<template id="matomo-config" data-url="https://stats.test" data-id="42"></template>'
  })

  afterEach(() => {
    delete window._paq
    document.head.innerHTML = ''
    for (const cookie of document.cookie.split('; ')) {
      document.cookie = `${cookie.split('=')[0]}=; Path=/; Max-Age=0`
    }
  })

  it('starts Matomo on the current page when the visitor says yes', () => {
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: true })

    expect(document.getElementById('matomo-config')).toBeNull()
    expect(window._paq).toContainEqual(['setSiteId', '42'])
    expect(window._paq).toContainEqual(['setTrackerUrl', 'https://stats.test/matomo.php'])
    expect(commands()).toContain('trackPageView')
    expect(matomoScripts().map((s) => s.src)).toEqual(['https://stats.test/matomo.js'])
  })

  it('starts Matomo even when another script already created _paq', () => {
    window._paq = [] as never
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: true })

    expect(commands()).toContain('trackPageView')
    expect(matomoScripts()).toHaveLength(1)
  })

  it('starts Matomo only once when the visitor says yes, no, then yes', () => {
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: true })
    consent.answer({ measurement: false }, { measurement: true })
    consent.answer({ measurement: true }, { measurement: false })

    expect(matomoScripts()).toHaveLength(1)
    expect(commands().at(-1)).toBe('setConsentGiven')
  })

  it('does nothing on a refusal before any yes', () => {
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: false })

    expect(document.getElementById('matomo-config')).not.toBeNull()
    expect(matomoScripts()).toEqual([])
  })

  it('does not load Matomo a second time when the server already did', () => {
    serverLoadedMatomo()
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: true }, { measurement: true })

    expect(matomoScripts()).toEqual([])
    expect(commands()).toEqual(['trackPageView'])
  })

  it('deletes the tracking cookies and stops tracking on a withdrawal', () => {
    serverLoadedMatomo()
    document.cookie = '_pk_id.42.abcd=visitor; Path=/'
    document.cookie = '_pk_ses.42.abcd=1; Path=/'
    document.cookie = 'mtm_consent_removed=1; Path=/'
    document.cookie = 'comparia_cookie_consent=1.0.1; Path=/'
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: false }, { measurement: true })

    expect(document.cookie).not.toContain('_pk_')
    expect(document.cookie).toContain('mtm_consent_removed=1')
    expect(document.cookie).toContain('comparia_cookie_consent=')
    expect(commands()).toContain('requireConsent')
  })

  it('resumes tracking when the visitor says yes again in the same visit', () => {
    serverLoadedMatomo()
    const consent = fakeConsent()
    followMeasurementConsent(consent)

    consent.answer({ measurement: false }, { measurement: true })
    consent.answer({ measurement: true }, { measurement: false })

    expect(commands().at(-1)).toBe('setConsentGiven')
    expect(matomoScripts()).toEqual([])
  })
})
