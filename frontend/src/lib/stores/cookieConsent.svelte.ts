import {
  COOKIE_CONSENT_MAX_AGE,
  COOKIE_CONSENT_NAME,
  decideCookieConsent,
  parseCookieConsent,
  serializeCookieConsent,
  type CookieChoice
} from '$lib/cookieConsent'
import { readCookie, secureAttribute } from '$lib/cookies'
import { createContext } from 'svelte'

export type CookieConsentListener = (choice: CookieChoice, previous: CookieChoice | null) => void

function readConsentCookie(): string | null {
  return readCookie(COOKIE_CONSENT_NAME) ?? null
}

function writeConsentCookie(value: string) {
  document.cookie = `${COOKIE_CONSENT_NAME}=${value}; Path=/; Max-Age=${COOKIE_CONSENT_MAX_AGE}; SameSite=Lax${secureAttribute()}`
}

export function createCookieConsent({
  enabled,
  measured,
  hasText,
  now = () => undefined
}: {
  // null when the server could not read the switch.
  enabled: () => boolean | null
  // Whether the page was rendered with audience measurement in use.
  measured: () => boolean
  // False when the banner text failed to load, so the banner cannot show.
  hasText: () => boolean
  now?: () => Date | undefined
}) {
  // The answer is known as soon as the browser creates the store, so nothing
  // acts on a false "not asked". The banner itself waits for load(), once
  // mounted, because the server renders without it.
  let loaded = $state(false)
  let value = $state(typeof document === 'undefined' ? null : readConsentCookie())
  let reopened = $state(false)
  // Where focus goes back once a reopened banner closes.
  let opener: HTMLElement | null = null
  let listeners: CookieConsentListener[] = []

  const consent = $derived(parseCookieConsent(value, now()))
  const choice = $derived<CookieChoice | null>(
    consent ? { measurement: consent.measurement } : null
  )
  const decision = $derived(
    decideCookieConsent({ switchOn: enabled(), measured: measured() }, value, now())
  )
  // With nothing measured there is no question, and without its text no
  // banner, so nothing to reopen either.
  const asking = $derived(enabled() === true && measured() && hasText())

  function hide() {
    if (!reopened) return
    reopened = false
    opener?.focus()
    opener = null
  }

  return {
    get asking() {
      return asking
    },
    get choice() {
      return choice
    },
    get decision() {
      return decision
    },
    get bannerOpen() {
      return loaded && asking && (decision.showBanner || reopened)
    },
    load() {
      value = readConsentCookie()
      loaded = true
    },
    reopen() {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      reopened = true
    },
    close: hide,
    save(next: CookieChoice) {
      const previous = choice
      value = serializeCookieConsent(next, now())
      writeConsentCookie(value)
      hide()
      for (const listener of listeners) listener(next, previous)
    },
    onChange(listener: CookieConsentListener) {
      listeners = [...listeners, listener]
      return () => {
        listeners = listeners.filter((l) => l !== listener)
      }
    }
  }
}

export type CookieConsentState = ReturnType<typeof createCookieConsent>

const [getCookieConsentContext, setCookieConsentContext] = createContext<CookieConsentState>()

export function provideCookieConsentContext(options: Parameters<typeof createCookieConsent>[0]) {
  return setCookieConsentContext(createCookieConsent(options))
}

export { getCookieConsentContext }
