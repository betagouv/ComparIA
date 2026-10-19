import { resolve } from '$app/paths'
import type { ResolvedPathname } from '$app/types'
import { legalLinks } from '$lib/consent'
import type {
  InformationalLegalPageLink,
  InformationalLegalPageLinks
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import type { AnyLinkProps, ExternalHref } from '$lib/routing'
import { getExternalLinkProps, validExternalUrl } from '$lib/routing'
import { createContext } from 'svelte'

export type InformationalPageKey = keyof InformationalLegalPageLinks
export type InformationalPageSurface = 'legal_menu' | 'settings'

export type InformationalPage = {
  mode: 'internal' | 'external'
  external_url: ExternalHref | null
  visible_in_legal_menu: boolean
  visible_in_settings: boolean
  content_by_locale: Record<string, string>
}

export type InformationalPages = Record<InformationalPageKey, InformationalPage>

const INFORMATIONAL_PAGE_KEYS = [
  'legal_notice',
  'accessibility',
  'ecodesign'
] as const satisfies InformationalPageKey[]
export const INFORMATIONAL_PAGE_PATHS: Record<InformationalPageKey, ResolvedPathname> = {
  legal_notice: resolve('/legal'),
  accessibility: resolve('/accessibility'),
  ecodesign: resolve('/eco-design')
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
  links: InformationalLegalPageLinks
): AnyLinkProps {
  const link = links[key]!
  return link.mode === 'external' && link.external_url
    ? getExternalLinkProps(link.external_url as ExternalHref)
    : { href: INFORMATIONAL_PAGE_PATHS[key] }
}

export function isInformationalPageVisible(
  link: InformationalLegalPageLink,
  surface: InformationalPageSurface
): boolean {
  return link[`visible_in_${surface}`]!
}

export function localizedInformationalContent(
  page: InformationalPage,
  locale: string
): string | null {
  return page.content_by_locale[locale] || page.content_by_locale.fr || null
}

export type LegalLinksContext = {
  legalMenuLinks: ({ label: string } & AnyLinkProps)[]
  settingsMenuLinks: ({ label: string } & AnyLinkProps)[]
}

const [getLegalLinksContext, setLegalLinksContext] = createContext<LegalLinksContext>()

export function _createLegalLinksContext(source: () => InformationalLegalPageLinks) {
  const links = $derived(source())

  const infoLinks = $derived(
    INFORMATIONAL_PAGE_KEYS.map((key) => ({
      key,
      label: m[`footer.links.${key}`](),
      ...informationalPageLinkProps(key, links)
    }))
  )

  const state: LegalLinksContext = {
    get legalMenuLinks() {
      return [
        ...legalLinks(),
        ...infoLinks.filter((link) => isInformationalPageVisible(links[link.key]!, 'legal_menu'))
      ]
    },
    get settingsMenuLinks() {
      return [
        ...legalLinks(),
        ...infoLinks.filter((link) => isInformationalPageVisible(links[link.key]!, 'settings'))
      ]
    }
  }

  return state
}
export function provideLegalLinksContext(source: () => InformationalLegalPageLinks) {
  const state = _createLegalLinksContext(source)
  setLegalLinksContext(state)
  return state
}

export { getLegalLinksContext }
