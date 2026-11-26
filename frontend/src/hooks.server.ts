import { env } from '$env/dynamic/private'
import { env as publicEnv } from '$env/dynamic/public'
import { TOTP_SETUP_PATH, UnauthorizedError, api, isTotpSetupRequired } from '$lib/fastapi-client'
import { COOKIE_CONSENT_NAME, decideCookieConsent } from '$lib/cookieConsent'
import { cookieMaxAge, defineCustomServerStrategy, type Locale } from '$lib/i18n/runtime'
import { paraglideMiddleware } from '$lib/i18n/server'
import { logger } from '$lib/logger.server'
import { fillMatomoPlaceholder, measurementInUse } from '$lib/matomo'
import { httpRequestCounter, httpRequestDuration } from '$lib/metrics'
import type { Handle, HandleFetch, HandleServerError } from '@sveltejs/kit'
import { redirect } from '@sveltejs/kit'
import { sequence } from '@sveltejs/kit/hooks'

// Cookies the backend identifies a visitor by. Server-side requests go to the
// API's internal origin, where the browser's cookies are not sent on their own.
const FORWARDED_COOKIES = ['auth_session', 'anonymous_session']

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  const apiOrigins = [
    publicEnv.PUBLIC_API_LOCAL_URL,
    publicEnv.PUBLIC_API_URL,
    'http://localhost:8001'
  ]
    .filter(Boolean)
    .map((url) => new URL(url!).origin)

  const requestUrl = new URL(request.url)
  if (requestUrl.pathname.startsWith('/api/') && apiOrigins.includes(requestUrl.origin)) {
    const headers = new Headers(request.headers)
    const existingCookies = headers.get('cookie')?.split('; ').filter(Boolean) ?? []
    // The anonymous session is the visitor's identity for everything they do
    // signed out (their answers, what they were already asked). Without it the
    // backend mints a fresh one for every server-side request.
    const forwarded = FORWARDED_COOKIES.flatMap((name) => {
      const value = event.cookies.get(name)
      const present = existingCookies.some((cookie) => cookie.startsWith(`${name}=`))
      return value && !present ? [`${name}=${value}`] : []
    })
    if (forwarded.length) {
      headers.set('cookie', [...existingCookies, ...forwarded].join('; '))
      request = new Request(request, { headers })
    }
  }

  return fetch(request)
}

function originOf(url: string): string | null {
  try {
    return new URL(url).origin
  } catch {
    return null
  }
}

// The API sits on another origin in dev, and Matomo on a host that can change
// from one request to the next, so both are added to the build-time policy from
// svelte.config.js instead of being hardcoded there.
const API_ORIGIN = originOf(publicEnv.PUBLIC_API_URL || '')

function withRuntimeOrigins(policy: string, matomoOrigin: string | null): string {
  const extraSources: Record<string, (string | null)[]> = {
    'script-src': [matomoOrigin],
    'connect-src': [matomoOrigin, API_ORIGIN],
    'img-src': [matomoOrigin, API_ORIGIN]
  }
  return policy
    .split('; ')
    .map((directive) => {
      const extra = (extraSources[directive.split(' ')[0]] ?? []).filter(
        (origin): origin is string => !!origin && !directive.includes(origin)
      )
      return extra.length ? `${directive} ${extra.join(' ')}` : directive
    })
    .join('; ')
}

export const securityHeadersHandle: Handle = async ({ event, resolve }) => {
  const response = await resolve(event)

  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')

  // Read after resolve, once cookieBannerHandle has worked out the measurement.
  // A request stopped before it, by a redirect, trusts no Matomo origin.
  const policy = response.headers.get('content-security-policy')
  if (policy) {
    const matomoOrigin = event.locals.measurement ? originOf(event.locals.measurement.url) : null
    response.headers.set('content-security-policy', withRuntimeOrigins(policy, matomoOrigin))
  }

  return response
}

const INSTANCE_CONFIG_TTL_MS = 20_000

type InstanceConfig = {
  enabled_locales: Locale[]
  default_locale?: Locale
  // null until the backend has answered once.
  cookie_banner_enabled: boolean | null
}

// Cached per Node process (same rationale as maintenanceCache below). The
// in-flight promise is cached rather than its result, so a cold process fires
// one request instead of one per concurrent render.
let instanceConfigCache: { promise: Promise<InstanceConfig>; checkedAt: number } | null = null
let lastInstanceConfig: InstanceConfig = {
  enabled_locales: [],
  cookie_banner_enabled: null
}

function getInstanceConfig(): Promise<InstanceConfig> {
  const now = Date.now()
  if (!instanceConfigCache || now - instanceConfigCache.checkedAt >= INSTANCE_CONFIG_TTL_MS) {
    instanceConfigCache = {
      checkedAt: now,
      promise: api
        .request<Partial<InstanceConfig>>('/auth/config')
        .then((config) => {
          lastInstanceConfig = {
            enabled_locales: config.enabled_locales ?? [],
            default_locale: config.default_locale,
            cookie_banner_enabled: config.cookie_banner_enabled ?? null
          }
          return lastInstanceConfig
        })
        .catch((error) => {
          // Fail open: keep serving the last known settings, and let Paraglide's
          // own strategies decide if we never managed to read any.
          logger.error('Instance config fetch failed', { error: `${error}` })
          return lastInstanceConfig
        })
    }
  }
  return instanceConfigCache.promise
}

defineCustomServerStrategy('custom-url', {
  // Paraglide runs custom strategies before every built-in one, so this is the
  // only place that sees all the locale sources at once, and the only place that
  // can turn one down. It reads PARAGLIDE_LOCALE itself instead of leaving it to
  // the built-in cookie strategy, because a cookie holding a locale the admin
  // has since disabled has to be overridden rather than honoured.
  //
  // Returning undefined hands over to those built-in strategies, which is what
  // we want when the backend is unreachable and we have nothing to enforce.
  getLocale: async (request) => {
    if (!request) return
    const { enabled_locales, default_locale } = await getInstanceConfig()
    if (!enabled_locales.length) return

    const cookieLocale = request.headers
      .get('cookie')
      ?.split('; ')
      .find((c) => c.startsWith('PARAGLIDE_LOCALE='))
      ?.split('=')[1]

    const requested = new URL(request.url).searchParams.get('locale')
    for (const candidate of [requested, cookieLocale]) {
      const enabled = enabled_locales.find((locale) => locale === candidate)
      if (enabled) return enabled
    }

    return default_locale
  }
})

export const handleError: HandleServerError = async ({ error, event }) => {
  if (isTotpSetupRequired(error)) {
    redirect(302, TOTP_SETUP_PATH)
  }
  if (error instanceof UnauthorizedError) {
    const path = event.url.pathname
    redirect(302, `/login?redirect=${encodeURIComponent(path)}`)
  }
  console.error(error)
}

// Read once per request: the page, its Matomo tag, the security header and
// the browser (through the root layout) all follow this one switch value and
// this one measurement.
export const cookieBannerHandle: Handle = async ({ event, resolve }) => {
  event.locals.cookieBannerEnabled = (await getInstanceConfig()).cookie_banner_enabled
  event.locals.measurement = measurementInUse({
    MATOMO_URL: env.MATOMO_URL,
    MATOMO_ID: env.MATOMO_ID
  })
  event.locals.cookieConsent = decideCookieConsent(
    { switchOn: event.locals.cookieBannerEnabled, measured: event.locals.measurement !== null },
    event.cookies.get(COOKIE_CONSENT_NAME)
  )
  return resolve(event)
}

// Audience measurement reaches the page only when the visitor's consent, or a
// switched-off banner, allows it. A cold start with the backend down leaves it
// out: the switch may be on, and nobody has been asked.
export const matomoHandle: Handle = ({ event, resolve }) => {
  const { measurement, cookieConsent } = event.locals
  return resolve(event, {
    transformPageChunk: ({ html }) =>
      fillMatomoPlaceholder(html, measurement, cookieConsent.loadMeasurement)
  })
}

// creating a handle to use the paraglide middleware
export const paraglideHandle: Handle = ({ event, resolve }) => {
  return paraglideMiddleware(event.request, ({ request: localizedRequest, locale }) => {
    event.request = localizedRequest
    if (locale !== event.cookies.get('PARAGLIDE_LOCALE')) {
      // Same lifetime as the cookie Paraglide sets in the browser.
      event.cookies.set('PARAGLIDE_LOCALE', locale, {
        path: '/',
        httpOnly: false,
        maxAge: cookieMaxAge
      })
    }

    return resolve(event, {
      transformPageChunk: ({ html }) => {
        return html
          .replaceAll('%lang%', locale)
          .replace('%scheme%', event.cookies.get('scheme') || 'system')
          .replace('%theme%', event.cookies.get('theme') || 'system')
      }
    })
  })
}

const MAINTENANCE_PATH = '/maintenance'
const MAINTENANCE_CHECK_TTL_MS = 20_000

// Cached per Node process so we don't hit the backend on every single request
let maintenanceCache: { enabled: boolean; checkedAt: number } | null = null

// Maintenance mode: re-checked at most every MAINTENANCE_CHECK_TTL_MS, so a
// fresh navigation sees the flag within that window (unlike client-side
// polling, already-open idle tabs are only caught on their next navigation).
const maintenanceHandle: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith(MAINTENANCE_PATH) || event.url.pathname.startsWith('/_app')) {
    return resolve(event)
  }

  const now = Date.now()
  if (!maintenanceCache || now - maintenanceCache.checkedAt >= MAINTENANCE_CHECK_TTL_MS) {
    let enabled = maintenanceCache?.enabled ?? false
    try {
      ;({ enabled } = await api.request<{ enabled: boolean }>('/maintenance/status', {
        fetch: event.fetch
      }))
    } catch (error) {
      // Fail open: don't take the whole site down if the status check itself fails
      logger.error('Maintenance status check failed', { error: `${error}` })
    }
    maintenanceCache = { enabled, checkedAt: now }
  }

  if (maintenanceCache.enabled) {
    redirect(307, MAINTENANCE_PATH)
  }

  return resolve(event)
}

// Metrics middleware
export const metricsHandle: Handle = async ({ event, resolve }) => {
  // Skip metrics endpoint itself
  if (event.url.pathname === '/metrics') {
    return resolve(event)
  }

  const start = Date.now()
  const response = await resolve(event)
  const duration = (Date.now() - start) / 1000

  const labels = {
    method: event.request.method,
    // Never the raw path: each label value is a series kept for the life of
    // the process, so anyone sending random URLs would grow it until it dies.
    route: event.route?.id ?? 'unmatched',
    status: response.status.toString()
  }

  httpRequestCounter.inc(labels)
  httpRequestDuration.observe(labels, duration)

  // The route id, not the path: /invite/[token] carries a sign-in credential
  // in its last segment, and logs travel further than mailboxes.
  logger.info('HTTP request', {
    method: event.request.method,
    route: event.route?.id ?? event.url.pathname.replace(/(\/invite\/)[^/?]+/, '$1<redacted>'),
    status: response.status,
    duration_ms: Math.round(Date.now() - start),
    user_agent: event.request.headers.get('user-agent')
  })

  return response
}

export const authWallHandle: Handle = async ({ event, resolve }) => {
  if (env.AUTH_ACCESS_POLICY !== 'sign_in_required') return resolve(event)

  const path = event.url.pathname
  if (path.startsWith('/login') || path.startsWith('/_app') || path.startsWith(MAINTENANCE_PATH))
    return resolve(event)

  const cookie = event.cookies.get('auth_session')
  if (!cookie) {
    redirect(302, `/login?redirect=${encodeURIComponent(path)}`)
  }

  // Holding a cookie is not the same as holding a session: anyone can set one
  // by hand. The backend answers from another host in every deployment, so
  // event.fetch will not carry the cookie on its own and we pass it along.
  let session: { user: unknown }
  try {
    session = await api.request<{ user: unknown }>('/auth/me', {
      fetch: event.fetch,
      headers: { cookie: `auth_session=${cookie}` }
    })
  } catch (error) {
    // Fail open, like the maintenance and locale checks above: a backend blip
    // must not sign everyone out, and the API guards its own endpoints anyway.
    logger.error('Auth wall session check failed', { error: `${error}` })
    return resolve(event)
  }

  if (!session.user) {
    event.cookies.delete('auth_session', { path: '/' })
    redirect(302, `/login?redirect=${encodeURIComponent(path)}`)
  }

  return resolve(event)
}

// securityHeadersHandle comes first so it sees the finished response, including
// the Content-Security-Policy SvelteKit sets when it renders a page.
export const handle = sequence(
  securityHeadersHandle,
  maintenanceHandle,
  authWallHandle,
  metricsHandle,
  cookieBannerHandle,
  matomoHandle,
  paraglideHandle
)
