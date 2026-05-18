import { env } from '$env/dynamic/private'
import { HOST_TO_LOCALE } from '$lib/global.svelte'
import { defineCustomServerStrategy } from '$lib/i18n/runtime'
import { paraglideMiddleware } from '$lib/i18n/server'
import { logger } from '$lib/logger.server'
import { httpRequestCounter, httpRequestDuration } from '$lib/metrics'
import type { Handle } from '@sveltejs/kit'

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
      return DEFAULT_LOCALE
    }
  }
})

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
		duration_ms: Math.round((Date.now() - start)),
		user_agent: event.request.headers.get('user-agent')
	})

	return response
}

// Compose handles: metrics first, then paraglide
export const handle: Handle = async ({ event, resolve }) => {
	return metricsHandle({ event, resolve: (e) => paraglideHandle({ event: e, resolve }) })
}
