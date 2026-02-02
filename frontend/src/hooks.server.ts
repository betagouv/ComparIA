import { env } from '$env/dynamic/private'
import { HOST_TO_LOCALE } from '$lib/global.svelte'
import { defineCustomServerStrategy } from '$lib/i18n/runtime'
import { paraglideMiddleware } from '$lib/i18n/server'
import { handleErrorWithSentry, sentryHandle } from '@sentry/sveltekit'
import { sequence } from '@sveltejs/kit/hooks'
import type { Handle } from '@sveltejs/kit'
import * as Sentry from '@sentry/sveltekit'

const MATOMO_ID = env.MATOMO_ID || ''
const MATOMO_URL = env.MATOMO_URL || ''
const SENTRY_FRONT_DSN = env.SENTRY_FRONT_DSN || ''

if (SENTRY_FRONT_DSN) {
  Sentry.init({
    dsn: SENTRY_FRONT_DSN,
    tracesSampleRate: 1.0
  })
}

defineCustomServerStrategy('custom-url', {
  getLocale: (request) => {
    if (!request) return
    const url = new URL(request.url)
    const locale = url.searchParams.get('locale')

    if (url.host in HOST_TO_LOCALE) {
      return HOST_TO_LOCALE[url.host as keyof typeof HOST_TO_LOCALE]
    } else if (locale) {
      return locale
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

export const handle: Handle = sequence(sentryHandle(), paraglideHandle)

export const handleError = handleErrorWithSentry()
