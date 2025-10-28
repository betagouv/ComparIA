import { paraglideMiddleware } from '$lib/i18n/server'
import type { Handle } from '@sveltejs/kit'
import { env } from '$env/dynamic/private'

const MATOMO_ID = env.MATOMO_ID || ''
const MATOMO_URL = env.MATOMO_URL || ''


// creating a handle to use the paraglide middleware
const paraglideHandle: Handle = ({ event, resolve }) =>
  paraglideMiddleware(event.request, ({ request: localizedRequest, locale }) => {
    event.request = localizedRequest

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

export const handle: Handle = paraglideHandle
