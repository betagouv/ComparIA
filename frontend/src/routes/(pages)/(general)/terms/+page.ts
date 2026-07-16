import { api } from '$lib/fastapi-client'
import type { AppSettingsPublic } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async () => {
  const settings = await api.request<AppSettingsPublic>('/settings')

  return {
    termsContent: settings.terms_content
  }
}
