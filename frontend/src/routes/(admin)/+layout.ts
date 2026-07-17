import type { AuthUser } from '$lib/auth.svelte'
import { api } from '$lib/fastapi-client'
import { redirect } from '@sveltejs/kit'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ url, fetch }) => {
  // Requery auth in case of recent login, parent raw data may not be updated
  const auth = await api.request<{ user: AuthUser | null }>('/auth/me', { fetch })

  if (!(auth.user?.role === 'admin')) {
    redirect(302, `/login?redirect=${encodeURIComponent(url.pathname)}`)
  }
}
