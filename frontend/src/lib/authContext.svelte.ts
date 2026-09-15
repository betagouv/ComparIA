import { createContext } from 'svelte'

export interface AuthUser {
  email: string
  role: string
}

export interface AuthConfig {
  access_policy: 'anonymous_first' | 'sign_in_required'
  methods: 'email_code'[]
  smtp_configured: boolean
  domain_allowlist: string[]
  platform_name: string
  platform_url: string
  has_custom_logo: boolean
  primary_color_light: string
  primary_color_dark: string
  secondary_color_light: string
  secondary_color_dark: string
  homepage_url: string | null
  enabled_locales: string[]
  default_locale: string
}

export type AuthCtx = {
  user: AuthUser | null
  config: AuthConfig
}

export const [getAuthContext, baseSetAuthContext] = createContext<AuthCtx>()

/**
 * The auth context when a parent set one, otherwise null. Components that only
 * read branding should not force every test rendering them to build a context,
 * and should not take a page down when there is none.
 */
export function tryGetAuthContext(): AuthCtx | null {
  try {
    return getAuthContext()
  } catch {
    return null
  }
}

export function setAuthContext(data: AuthCtx) {
  const auth = $state(data)
  baseSetAuthContext(auth)
  return auth
}
