import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { updateComparisonsContext, type ComparisonsCtx } from '$lib/chatService.svelte'
import { resetConsent } from '$lib/consent'
import { api } from '$lib/fastapi-client'
import type { AuthCtx, AuthUser } from '$lib/authContext.svelte'

// The context lives in authContext.svelte.ts so that components which only read
// it are not made to import this module's API client and navigation helpers.
export {
  getAuthContext,
  setAuthContext,
  tryGetAuthContext,
  type AuthConfig,
  type AuthCtx,
  type AuthUser
} from '$lib/authContext.svelte'

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
      goto(resolve('/'))
    }
  }
}
