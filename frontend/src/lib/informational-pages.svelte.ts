import type { ResolvedPathname } from '$app/types'
import { ACCESSIBILITY_PATH, ECODESIGN_PATH, LEGAL_NOTICE_PATH, legalLinks } from '$lib/consent'
import type {
  InformationalLegalPageLink,
  InformationalLegalPageLinks
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import type { AnyLinkProps, ExternalHref } from '$lib/routing'
import { getExternalLinkProps } from '$lib/routing'
import { createContext } from 'svelte'

export type InformationalPageKey = keyof InformationalLegalPageLinks
export type InformationalPageSurface = 'legal_menu' | 'settings'

const INFORMATIONAL_PAGE_KEYS = [
  'legal_notice',
  'accessibility',
  'ecodesign'
] as const satisfies InformationalPageKey[]
export const INFORMATIONAL_PAGE_PATHS: Record<InformationalPageKey, ResolvedPathname> = {
  legal_notice: LEGAL_NOTICE_PATH,
  accessibility: ACCESSIBILITY_PATH,
  ecodesign: ECODESIGN_PATH
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
