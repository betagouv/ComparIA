import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { updateComparisonsContext, type ComparisonsCtx } from '$lib/chatService.svelte'
import { resetConsent } from '$lib/consent'
import { api } from '$lib/fastapi-client'
import { createContext } from 'svelte'

export interface AuthUser {
  email: string
  role: string
}

export interface AuthConfig {
  access_policy: 'anonymous_first' | 'sign_in_required'
  methods: ('email_code' | 'oidc')[]
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
  // OIDC method description for the login page. `oidc_enabled` is derived
  // server-side from `methods` plus a complete provider config, so the button
  // only renders when OIDC would actually work.
  oidc_enabled: boolean
  oidc_button_label: string | null
  oidc_has_button_logo: boolean
}

type AuthCtx = {
  user: AuthUser | null
  config: AuthConfig
}
export const [getAuthContext, baseSetAuthContext] = createContext<AuthCtx>()

export function setAuthContext(data: AuthCtx) {
  const auth = $state(data)
  baseSetAuthContext(auth)
  return auth
}

export function userAllowed(auth: AuthCtx, role?: AuthUser['role']) {
  if (!role) return true
  return auth.user?.role === role
}

export function openSignInModal(): void {
  const el = document.getElementById('fr-modal-signin')
  if (el) {
    // @ts-expect-error - DSFR is globally available
    window.dsfr(el).modal.disclose()
  }
}

export async function logout(auth: AuthCtx, comparisons: ComparisonsCtx): Promise<void> {
  try {
    await api.request<void>('/auth/logout', { method: 'POST' })
    try {
      await updateComparisonsContext(comparisons)
    } catch {
      // Session is already cleared server-side; querying again can fail
      // (eg. sign_in_required policy blocks /arena/* without a session).
      comparisons.length = 0
    }
  } finally {
    auth.user = null
    // The account's acceptance says nothing about the anonymous visitor left
    // behind, so the next page must ask the server again.
    resetConsent()
    if (auth.config?.access_policy === 'sign_in_required') {
      goto(resolve('/login'))
    } else {
      goto(resolve('/arene'))
    }
  }
}
