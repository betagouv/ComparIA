import { browser } from '$app/environment'
import { goto } from '$app/navigation'
import { api } from '$lib/fastapi-client'

export interface AuthUser {
  email: string
  role: string
}

export interface AuthConfig {
  access_policy: 'anonymous_first' | 'sign_in_required'
  methods: 'email_code'[]
  smtp_configured: boolean
  domain_allowlist: string[]
}

export const auth = $state<{ user: AuthUser | null; config: AuthConfig | null }>({
  user: null,
  config: null
})

export function isAdmin(): boolean {
  return auth.user?.role === 'admin'
}

export async function initAuth(): Promise<void> {
  if (!browser) return

  try {
    auth.config = await api.request<AuthConfig>('/auth/config')
  } catch {
    // silently ignore
  }

  try {
    const data = await api.request<{ user: AuthUser | null }>('/auth/me', { credentials: 'include' })
    auth.user = data.user
  } catch {
    auth.user = null
  }
}

export function openSignInModal(): void {
  const el = document.getElementById('fr-modal-signin')
  if (el) {
    // @ts-expect-error - DSFR is globally available
    window.dsfr(el).modal.disclose()
  }
}

export async function logout(): Promise<void> {
  try {
    await api.request<void>('/auth/logout', { method: 'POST', credentials: 'include' })
  } finally {
    auth.user = null
    if (auth.config?.access_policy === 'sign_in_required') {
      goto('/login')
    }
  }
}
