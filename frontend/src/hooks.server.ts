import { env } from '$env/dynamic/private'
import { api, UnauthorizedError } from '$lib/fastapi-client'
import { HOST_TO_LOCALE } from '$lib/global.svelte'
import { defineCustomServerStrategy } from '$lib/i18n/runtime'
import { paraglideMiddleware } from '$lib/i18n/server'
import { logger } from '$lib/logger.server'
import { httpRequestCounter, httpRequestDuration } from '$lib/metrics'
import type { Handle, HandleServerError } from '@sveltejs/kit'
import { redirect } from '@sveltejs/kit'
import { sequence } from '@sveltejs/kit/hooks'

const MATOMO_ID = env.MATOMO_ID || ''
const MATOMO_URL = env.MATOMO_URL || ''

const DEFAULT_LOCALE = env.DEFAULT_LOCALE || ''

defineCustomServerStrategy('custom-url', {
  getLocale: (request) => {
    if (!request) return
    const url = new URL(request.url)
    const locale = url.searchParams.get('locale')

    if (url.host in HOST_TO_LOCALE) {
      return HOST_TO_LOCALE[url.host as keyof typeof HOST_TO_LOCALE]
    } else if (locale) {
      return locale
    } else if (DEFAULT_LOCALE) {
      // Only apply DEFAULT_LOCALE if no user cookie is already set.
      // Paraglide runs custom strategies before built-in ones (including cookie),
      // so without this check DEFAULT_LOCALE would silently override the user's
      // locale preference stored in PARAGLIDE_LOCALE.
      const cookieLocale = request.headers
        .get('cookie')
        ?.split('; ')
        .find((c) => c.startsWith('PARAGLIDE_LOCALE='))
        ?.split('=')[1]
      if (!cookieLocale) {
        return DEFAULT_LOCALE
      }
    }
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
