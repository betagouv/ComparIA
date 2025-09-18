import { MATOMO_ID, MATOMO_URL } from '$env/static/private'
import { paraglideMiddleware } from '$lib/i18n/server'
import type { Handle } from '@sveltejs/kit'

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
