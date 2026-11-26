// Audience measurement, loaded only when the cookie consent decision allows it.
// The server writes the tracker into the page; the browser starts it on a yes
// given mid-visit and stops it on a withdrawal.

import { secureAttribute } from '$lib/cookies'
import type { AuthConfig } from '$lib/generated/backend'
import type { CookieConsentListener } from '$lib/stores/cookieConsent.svelte'

export type MatomoConfig = { url: string; id: string }
// The Matomo a request measures with, or null when nothing is measured.
export type Measurement = MatomoConfig | null

// The admin's setting from the instance config: true measures with the
// admin's address and site id, false is Off, null follows the server's
// environment.
export type MeasurementSetting = Pick<
  AuthConfig,
  'matomo_enabled' | 'matomo_url' | 'matomo_site_id'
>

// A setting never read, after a failed fetch on a cold process, is not taken
// for Off: the server's environment decides, as it did before the setting
// existed. The environment needs both values; the backend refuses On without
// both.
export function measurementInUse(
  setting: MeasurementSetting | null,
  env: { MATOMO_URL?: string; MATOMO_ID?: string }
): Measurement {
  if (setting?.matomo_enabled === false) return null
  if (setting?.matomo_enabled === true) {
    const { matomo_url: url, matomo_site_id: id } = setting
    return url && id ? { url, id } : null
  }
  const url = env.MATOMO_URL || ''
  const id = env.MATOMO_ID || ''
  return url && id ? { url, id } : null
}

// app.html carries `<!-- matomo %sveltekit.nonce% -->`, filled in by the server.
const PLACEHOLDER = /<!-- matomo (\S*) -->/

// The same markup app.html held before the consent banner existed.
const MARKUP = `<!-- Matomo -->
    <script nonce="%nonce%">
      var _paq = (window._paq = window._paq || [])
      /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
      _paq.push(['enableLinkTracking'])
      /* No HeatmapSessionRecording: it captured mouse movement and DOM changes
         for the whole visit, and nobody watched the recordings. */
      /* An invite link is a sign-in credential; keep the token off the
         analytics host. */
      if (/^\\/invite\\/[^/]+/.test(location.pathname)) {
        _paq.push(['setCustomUrl', location.origin + '/invite/<redacted>'])
      }
      _paq.push(['trackPageView'])
      ;(function () {
        var u = %matomo_url_js% + '/'
        _paq.push(['setTrackerUrl', u + 'matomo.php'])
        _paq.push(['setSiteId', %matomo_id_js%])
        var d = document,
          g = d.createElement('script'),
          s = d.getElementsByTagName('script')[0]
        g.async = true
        g.src = u + 'matomo.js'
        s.parentNode.insertBefore(g, s)
      })()
    </script>
    <noscript
      ><p>
        <img
          referrerpolicy="no-referrer-when-downgrade"
          src="%matomo_url_attr%/matomo.php?idsite=%matomo_id_attr%&amp;rec=1"
          style="border: 0"
          alt=""
        /></p
    ></noscript>
    <!-- End Matomo Code -->`

const CONFIG_ID = 'matomo-config'

function escapeAttribute(value: string): string {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;')
}

// A string literal that cannot close the inline script it sits in. The
// environment values reach here unchecked.
function scriptString(value: string): string {
  return JSON.stringify(value).replaceAll('<', '\\u003c').replaceAll('>', '\\u003e')
}

// Without consent the page still says where Matomo lives, in an inert element,
// so the browser can start it if the visitor says yes later. An instance with
// no measurement gets neither.
export function fillMatomoPlaceholder(html: string, config: Measurement, load: boolean): string {
  return html.replace(PLACEHOLDER, (_match, nonce: string) => {
    if (!config) return ''
    if (!load)
      return `<template id="${CONFIG_ID}" data-url="${escapeAttribute(config.url)}" data-id="${escapeAttribute(config.id)}"></template>`
    return MARKUP.replace('%nonce%', () => nonce)
      .replaceAll('%matomo_url_js%', () => scriptString(config.url))
      .replaceAll('%matomo_id_js%', () => scriptString(config.id))
      .replaceAll('%matomo_url_attr%', () => escapeAttribute(config.url))
      .replaceAll('%matomo_id_attr%', () => escapeAttribute(config.id))
  })
}

type Paq = { push: (command: unknown[]) => void }

declare global {
  interface Window {
    _paq?: Paq
  }
}

// The browser twin of MARKUP's script, for a yes given after the page loaded.
function startMatomo({ url, id }: MatomoConfig) {
  const paq: Paq = (window._paq = window._paq || ([] as unknown[][]))
  paq.push(['enableLinkTracking'])
  if (/^\/invite\/[^/]+/.test(location.pathname)) {
    paq.push(['setCustomUrl', location.origin + '/invite/<redacted>'])
  }
  paq.push(['trackPageView'])
  paq.push(['setTrackerUrl', `${url}/matomo.php`])
  paq.push(['setSiteId', id])
  const script = document.createElement('script')
  script.async = true
  script.src = `${url}/matomo.js`
  document.head.appendChild(script)
  document.getElementById(CONFIG_ID)?.remove()
}

// Matomo's tracking cookies. mtm_consent_removed is left alone: it is the
// opt-out the privacy page writes, and deleting it would undo a refusal.
const TRACKING_COOKIE = /^(_pk_|mtm_consent$|mtm_cookie_consent$)/

function deleteTrackingCookies() {
  const names = document.cookie
    .split('; ')
    .map((cookie) => cookie.split('=')[0])
    .filter((name) => TRACKING_COOKIE.test(name))
  const host = location.hostname
  for (const name of names) {
    for (const domain of ['', `; domain=${host}`, `; domain=.${host}`]) {
      document.cookie = `${name}=; Path=/; Max-Age=0${domain}${secureAttribute()}`
    }
  }
}

function stopMatomo() {
  // requireConsent stops tracking for the rest of the visit without writing a
  // cookie, unlike optUserOut or forgetConsentGiven.
  window._paq?.push(['requireConsent'])
  window._paq?.push(['deleteCookies'])
  deleteTrackingCookies()
}

function readConfig(): MatomoConfig | null {
  const element = document.getElementById(CONFIG_ID)
  if (!element) return null
  return { url: element.dataset.url ?? '', id: element.dataset.id ?? '' }
}

export function followMeasurementConsent(consent: {
  onChange: (listener: CookieConsentListener) => () => void
}): () => void {
  return consent.onChange((choice, previous) => {
    if (!choice.measurement) {
      stopMatomo()
    } else if (previous?.measurement !== true) {
      const config = readConfig()
      if (config) {
        startMatomo(config)
      } else {
        // Only reached after a withdrawal earlier in this visit.
        window._paq?.push(['setConsentGiven'])
      }
    }
  })
}
