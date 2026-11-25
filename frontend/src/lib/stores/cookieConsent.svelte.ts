import {
  COOKIE_CONSENT_MAX_AGE,
  COOKIE_CONSENT_NAME,
  decideCookieConsent,
  parseCookieConsent,
  serializeCookieConsent,
  type CookieChoice
} from '$lib/cookieConsent'
import { createContext } from 'svelte'

export type CookieConsentListener = (choice: CookieChoice, previous: CookieChoice | null) => void

function readConsentCookie(): string | null {
  const prefix = `${COOKIE_CONSENT_NAME}=`
  const cookie = document.cookie.split('; ').find((c) => c.startsWith(prefix))
  return cookie ? cookie.slice(prefix.length) : null
}

function writeConsentCookie(value: string) {
  const secure = location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${COOKIE_CONSENT_NAME}=${value}; Path=/; Max-Age=${COOKIE_CONSENT_MAX_AGE}; SameSite=Lax${secure}`
}

export function createCookieConsent({
  enabled,
  now = () => undefined
}: {
  enabled: () => boolean
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
    consent ? { measurement: consent.measurement, preferences: consent.preferences } : null
  )
  const decision = $derived(decideCookieConsent(enabled(), value, now()))

  function hide() {
    if (!reopened) return
    reopened = false
    opener?.focus()
    opener = null
  }

  return {
    get choice() {
      return choice
    },
    get decision() {
      return decision
    },
    get bannerOpen() {
      return loaded && enabled() && (decision.showBanner || reopened)
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
