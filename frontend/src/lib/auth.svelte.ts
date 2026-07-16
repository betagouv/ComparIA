import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { api } from '$lib/fastapi-client'
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
  has_custom_logo: boolean
}

type AuthCtx = {
  user: AuthUser | null
  config: AuthConfig
}
export const [getAuthContext, baseSetAuthContext] = createContext<AuthCtx>()

export function setAuthContext(data: AuthCtx) {
  const auth = $state(data)
  baseSetAuthContext(auth)
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

export async function logout(auth: AuthCtx): Promise<void> {
  try {
    await api.request<void>('/auth/logout', { method: 'POST' })
  } finally {
    auth.user = null
    if (auth.config?.access_policy === 'sign_in_required') {
      goto(resolve('/login'))
    } else {
      goto(resolve('/arene'))
    }
  }
}
