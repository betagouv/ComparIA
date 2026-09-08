import { redirect } from '@sveltejs/kit'
import { localizedInformationalContent, type InformationalPageKey } from '$lib/informational-pages'
import { loadInformationalPages } from '$lib/informational-pages.server'
import { getLocale } from '$lib/i18n/runtime'

export async function loadInformationalPage(key: InformationalPageKey, fetcher: typeof fetch) {
  const pages = await loadInformationalPages(fetcher)
  const page = pages[key]
  if (page.mode === 'external' && page.external_url) redirect(307, page.external_url)
  return { content: localizedInformationalContent(page, getLocale()) }
}
