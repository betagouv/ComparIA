import {
  cookieMaxAge,
  cookieName,
  defineCustomClientStrategy,
  defineCustomServerStrategy,
  isLocale,
  type Locale
} from '$lib/i18n/runtime'
import { instanceCookiePath } from '$lib/routing'

// Paraglide's own `cookie` strategy always writes `path=/`, which every Instance
// served from the same origin would read. This one keeps the locale in the same
// cookie, on the Instance path, see ADR 0003. It takes the place of `cookie` in
// the strategy of vite.config.ts. Importing the module registers it.
export const LOCALE_COOKIE_STRATEGY = 'custom-cookie'

function localeIn(cookies: string | null | undefined): Locale | undefined {
  const value = cookies
    ?.split(';')
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${cookieName}=`))
    ?.slice(cookieName.length + 1)
  return value && isLocale(value) ? value : undefined
}

defineCustomClientStrategy(LOCALE_COOKIE_STRATEGY, {
  getLocale: () => localeIn(document.cookie),
  setLocale: (locale) => {
    const secure = location.protocol === 'https:' ? '; secure' : ''
    document.cookie = `${cookieName}=${locale}; path=${instanceCookiePath()}; max-age=${cookieMaxAge}; samesite=lax${secure}`
  }
})

defineCustomServerStrategy(LOCALE_COOKIE_STRATEGY, {
  getLocale: (request) => localeIn(request?.headers.get('cookie'))
})
