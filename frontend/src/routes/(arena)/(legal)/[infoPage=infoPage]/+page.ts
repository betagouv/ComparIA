import { api } from '$lib/fastapi-client'
import type { InformationalLegalPageContent } from '$lib/generated/backend'
import { getLocale } from '$lib/i18n/runtime'
import type { InformationalPageKey } from '$lib/informational-pages.svelte'
import { error, redirect } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ params, parent, fetch }) => {
  const infoPageKey = params.infoPage as InformationalPageKey
  const link = (await parent()).informationalPagesLinks[infoPageKey]

  if (!link) error(404)
  if (link.mode === 'external' && link.external_url) redirect(307, link.external_url)

  return {
    page: await api.request<InformationalLegalPageContent | null>(
      `/settings/legal/informational-page/${infoPageKey}`,
      { searchParams: { locale: getLocale() }, fetch }
    )
  }
}
