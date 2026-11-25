// Kept free of SvelteKit and browser imports: the server hook and the browser
// both decide through this module, so they can never disagree.

export const COOKIE_CONSENT_NAME = 'comparia_cookie_consent'
// Bump to ask everyone again, for instance when a new kind of cookie appears.
export const COOKIE_CONSENT_VERSION = 1
// About six months, then the banner asks again.
export const COOKIE_CONSENT_MAX_AGE = 182 * 24 * 60 * 60
// A visitor's clock can run ahead of ours; past this, the date is made up.
const CLOCK_SKEW_MS = 24 * 60 * 60 * 1000

export type CookieChoice = { measurement: boolean; preferences: boolean }
export type CookieConsent = CookieChoice & { givenAt: Date }
export type CookieConsentDecision = {
  showBanner: boolean
  loadMeasurement: boolean
  keepSettings: boolean
}

const flag = (value: boolean) => (value ? '1' : '0')

// Digits and dots only, so the value reads the same whether it went through
// SvelteKit's cookie decoding or straight out of document.cookie.
export function serializeCookieConsent(choice: CookieChoice, givenAt = new Date()): string {
  return [
    COOKIE_CONSENT_VERSION,
    flag(choice.measurement),
    flag(choice.preferences),
    Math.floor(givenAt.getTime() / 1000)
  ].join('.')
}

export function parseCookieConsent(
  value: string | null | undefined,
  now = new Date()
): CookieConsent | null {
  const match = value?.match(/^(\d+)\.([01])\.([01])\.(\d+)$/)
  if (!match) return null
  const [, version, measurement, preferences, timestamp] = match
  if (Number(version) !== COOKIE_CONSENT_VERSION) return null

  const givenAt = new Date(Number(timestamp) * 1000)
  const age = now.getTime() - givenAt.getTime()
  if (!Number.isFinite(age) || age >= COOKIE_CONSENT_MAX_AGE * 1000 || age < -CLOCK_SKEW_MS)
    return null

  return { measurement: measurement === '1', preferences: preferences === '1', givenAt }
}

// A null switch means the server never managed to read it. The banner may be
// on, so Matomo stays out, but without its text nothing can be asked, and
// settings stay where they are.
export function decideCookieConsent(
  switchOn: boolean | null,
  value: string | null | undefined,
  now = new Date()
): CookieConsentDecision {
  if (switchOn === null) return { showBanner: false, loadMeasurement: false, keepSettings: true }
  if (!switchOn) return { showBanner: false, loadMeasurement: true, keepSettings: true }

  const consent = parseCookieConsent(value, now)
  return {
    showBanner: !consent,
    loadMeasurement: consent?.measurement ?? false,
    keepSettings: consent?.preferences ?? false
  }
}
