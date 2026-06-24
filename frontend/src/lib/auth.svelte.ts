import { browser } from '$app/environment'
import { api } from '$lib/fastapi-client'

export interface AuthUser {
  email: string
}

export interface AuthConfig {
  access_policy: 'anonymous_first' | 'sign_in_required'
  methods: 'email_code'[]
}

export const auth = $state<{ user: AuthUser | null; config: AuthConfig | null }>({
  user: null,
  config: null
})

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

export async function logout(): Promise<void> {
  try {
    await api.request<void>('/auth/logout', { method: 'POST', credentials: 'include' })
  } finally {
    auth.user = null
  }
}
