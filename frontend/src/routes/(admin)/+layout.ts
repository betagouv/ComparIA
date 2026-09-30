import type { AuthUser } from '$lib/auth.svelte'
import { TOTP_SETUP_PATH, api } from '$lib/fastapi-client'
import { redirect } from '@sveltejs/kit'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ url, fetch }) => {
  // Requery auth in case of recent login, parent raw data may not be updated
  const auth = await api.request<{ user: AuthUser | null }>('/auth/me', { fetch })

  if (!(auth.user?.role === 'admin')) {
    redirect(302, `/login?redirect=${encodeURIComponent(url.pathname)}`)
  }
  // The backend refuses /admin/* until the authenticator is enrolled, so do
  // not let a page load run into that: send the admin to enrol first.
  if (!auth.user.totp_enabled) {
    redirect(302, TOTP_SETUP_PATH)
  }
}
