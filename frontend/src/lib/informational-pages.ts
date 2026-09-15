import type { ResolvedPathname } from '$app/types'
import type { AnyLinkProps, ExternalHref } from '$lib/routing'
import { getExternalLinkProps, validExternalUrl } from '$lib/routing'
export type InformationalPageKey = 'legal_notice' | 'accessibility' | 'ecodesign'
export type InformationalPageSurface = 'legal_menu' | 'settings'

export type InformationalPage = {
  mode: 'internal' | 'external'
  external_url: ExternalHref | null
  visible_in_legal_menu: boolean
  visible_in_settings: boolean
  content_by_locale: Record<string, string>
}

export type InformationalPages = Record<InformationalPageKey, InformationalPage>

export const INFORMATIONAL_PAGE_PATHS: Record<InformationalPageKey, ResolvedPathname> = {
  legal_notice: '/legal',
  accessibility: '/accessibility',
  ecodesign: '/eco-design'
}

const visibleInternalPage = (): InformationalPage => ({
  mode: 'internal',
  external_url: null,
  visible_in_legal_menu: true,
  visible_in_settings: true,
  content_by_locale: {}
})

/** Safe defaults mirror the links and built-in pages that predate configuration. */
export const DEFAULT_INFORMATIONAL_PAGES: InformationalPages = {
  legal_notice: visibleInternalPage(),
  accessibility: visibleInternalPage(),
  ecodesign: visibleInternalPage()
}

export function normalizeInformationalPages(value: unknown): InformationalPages {
  const source = (value as { pages?: Partial<InformationalPages> } | null)?.pages ?? {}
  return Object.fromEntries(
    (Object.keys(DEFAULT_INFORMATIONAL_PAGES) as InformationalPageKey[]).map((key) => {
      const fallback = DEFAULT_INFORMATIONAL_PAGES[key]
      const candidate = source[key]
      const externalUrl = validExternalUrl(candidate?.external_url)
      return [
        key,
        {
          ...fallback,
          ...candidate,
          mode: candidate?.mode === 'external' && externalUrl ? 'external' : 'internal',
          external_url: externalUrl,
          content_by_locale: candidate?.content_by_locale ?? {}
        }
      ]
    })
  ) as InformationalPages
}

export function informationalPageLinkProps(
  key: InformationalPageKey,
  pages: InformationalPages
): AnyLinkProps {
  const page = pages[key]
  return page.mode === 'external' && page.external_url
    ? getExternalLinkProps(page.external_url)
    : { href: INFORMATIONAL_PAGE_PATHS[key] }
}

export function isInformationalPageVisible(
  page: InformationalPage,
  surface: InformationalPageSurface
): boolean {
  return page[`visible_in_${surface}`]
}

export function localizedInformationalContent(
  page: InformationalPage,
  locale: string
): string | null {
  return page.content_by_locale[locale] || page.content_by_locale.fr || null
}
