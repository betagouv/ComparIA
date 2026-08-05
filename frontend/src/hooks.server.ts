import { env } from '$env/dynamic/private'
import { api, UnauthorizedError } from '$lib/fastapi-client'
import { defineCustomServerStrategy } from '$lib/i18n/runtime'
import { paraglideMiddleware } from '$lib/i18n/server'
import { logger } from '$lib/logger.server'
import { httpRequestCounter, httpRequestDuration } from '$lib/metrics'
import type { Handle, HandleServerError } from '@sveltejs/kit'
import { redirect } from '@sveltejs/kit'
import { sequence } from '@sveltejs/kit/hooks'

const MATOMO_ID = env.MATOMO_ID || ''
const MATOMO_URL = env.MATOMO_URL || ''

const LOCALE_SETTINGS_TTL_MS = 20_000

type LocaleSettings = { enabled_locales: string[]; default_locale: string }

// Cached per Node process (same rationale as maintenanceCache below). The
// in-flight promise is cached rather than its result, so a cold process fires
// one request instead of one per concurrent render.
let localeSettingsCache: { promise: Promise<LocaleSettings>; checkedAt: number } | null = null
let lastLocaleSettings: LocaleSettings = { enabled_locales: [], default_locale: '' }

function getLocaleSettings(): Promise<LocaleSettings> {
  const now = Date.now()
  if (!localeSettingsCache || now - localeSettingsCache.checkedAt >= LOCALE_SETTINGS_TTL_MS) {
    localeSettingsCache = {
      checkedAt: now,
      promise: api
        .request<Partial<LocaleSettings>>('/auth/config')
        .then((config) => {
          lastLocaleSettings = {
            enabled_locales: config.enabled_locales ?? [],
            default_locale: config.default_locale ?? ''
          }
          return lastLocaleSettings
        })
        .catch((error) => {
          // Fail open: keep serving the last known settings, and let Paraglide's
          // own strategies decide if we never managed to read any.
          logger.error('Locale settings fetch failed', { error: `${error}` })
          return lastLocaleSettings
        })
    }
  }
  return localeSettingsCache.promise
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
    const { enabled_locales, default_locale } = await getLocaleSettings()
    if (!enabled_locales.length) return

    const cookieLocale = request.headers
      .get('cookie')
      ?.split('; ')
      .find((c) => c.startsWith('PARAGLIDE_LOCALE='))
      ?.split('=')[1]

    const requested = new URL(request.url).searchParams.get('locale')
    for (const candidate of [requested, cookieLocale]) {
      if (candidate && enabled_locales.includes(candidate)) return candidate
    }

    return default_locale || undefined
  }
})

export const handleError: HandleServerError = async ({ error, event }) => {
  if (error instanceof UnauthorizedError) {
    const path = event.url.pathname
    redirect(302, `/login?redirect=${encodeURIComponent(path)}`)
  }
  console.error(error)
}

// creating a handle to use the paraglide middleware
const paraglideHandle: Handle = ({ event, resolve }) => {
  return paraglideMiddleware(event.request, ({ request: localizedRequest, locale }) => {
    event.request = localizedRequest
    if (locale !== event.cookies.get('PARAGLIDE_LOCALE')) {
      event.cookies.set('PARAGLIDE_LOCALE', locale, { path: '/', httpOnly: false })
    }

    return resolve(event, {
      transformPageChunk: ({ html }) => {
        return html
          .replaceAll('%lang%', locale)
          .replace('%scheme%', event.cookies.get('scheme') || 'system')
          .replace('%theme%', event.cookies.get('theme') || 'system')
          .replaceAll('%matomo_id%', MATOMO_ID)
          .replaceAll('%matomo_url%', MATOMO_URL)
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
const metricsHandle: Handle = async ({ event, resolve }) => {
  // Skip metrics endpoint itself
  if (event.url.pathname === '/metrics') {
    return resolve(event)
  }

  const start = Date.now()
  const response = await resolve(event)
  const duration = (Date.now() - start) / 1000

  const labels = {
    method: event.request.method,
    route: event.route?.id || event.url.pathname,
    status: response.status.toString()
  }

  httpRequestCounter.inc(labels)
  httpRequestDuration.observe(labels, duration)

  // Log request to Custom Logger
  logger.info('HTTP request', {
    method: event.request.method,
    path: event.url.pathname,
    route: event.route?.id,
    status: response.status,
    duration_ms: Math.round(Date.now() - start),
    user_agent: event.request.headers.get('user-agent')
  })

  return response
}

const authWallHandle: Handle = ({ event, resolve }) => {
  if (env.AUTH_ACCESS_POLICY !== 'sign_in_required') return resolve(event)

  const path = event.url.pathname
  if (path.startsWith('/login') || path.startsWith('/_app') || path.startsWith(MAINTENANCE_PATH))
    return resolve(event)

  const cookie = event.cookies.get('auth_session')
  if (!cookie) {
    redirect(302, `/login?redirect=${encodeURIComponent(path)}`)
  }

  return resolve(event)
}

export const handle = sequence(maintenanceHandle, authWallHandle, metricsHandle, paraglideHandle)
