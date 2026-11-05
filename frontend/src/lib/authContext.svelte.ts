import type { AuthConfig } from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import { createContext } from 'svelte'

export interface AuthUser {
  email: string
  role: string
  totp_enabled: boolean
  questions_answered: boolean
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

/**
 * The instance's name for copy that mentions it. Read at component init like
 * any context; the message fallback covers a page rendered without one.
 */
export function getPlatformName(): string {
  return tryGetAuthContext()?.config?.platform_name || m['header.title']()
}
