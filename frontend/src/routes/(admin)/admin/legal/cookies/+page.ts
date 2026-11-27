import { api } from '$lib/fastapi-client'
import type { AppSettingsPublic, TranslatableCookieBanner } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ data, depends, fetch }) => {
  depends('admin:legal')
  const [settings, banners] = await Promise.all([
    api.request<AppSettingsPublic>('/admin/settings', { fetch }),
    api.request<TranslatableCookieBanner>('/admin/legal/cookies', { fetch })
  ])
  return { ...data, settings, banners }
}
