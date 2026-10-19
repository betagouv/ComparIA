import { describe, expect, it } from 'vitest'
import {
  ACCESSIBILITY_PATH,
  ECODESIGN_PATH,
  LEGAL_NOTICE_PATH,
  PRIVACY_POLICY_PATH,
  TERMS_PATH
} from './consent'
import {
  _createLegalLinksContext,
  DEFAULT_INFORMATIONAL_PAGES,
  informationalPageLinkProps,
  isInformationalPageVisible,
  localizedInformationalContent,
  normalizeInformationalPages
} from './informational-pages.svelte'
import { informationalLegalPageLinks } from './testing/mock-data'

describe('informational legal pages', () => {
  it('keeps the seeded internal pages when no configuration is available', () => {
    expect(normalizeInformationalPages(null)).toEqual(DEFAULT_INFORMATIONAL_PAGES)
  })

  it('uses only safe external destinations and independent surface visibility', () => {
    const pages = normalizeInformationalPages({
      pages: {
        ecodesign: {
          ...DEFAULT_INFORMATIONAL_PAGES.ecodesign,
          mode: 'external',
          external_url: 'https://example.gouv.fr/eco-design',
          visible_in_settings: false
        }
      }
    })

    expect(informationalPageLinkProps('ecodesign', pages).href).toBe(
      'https://example.gouv.fr/eco-design'
    )
    expect(isInformationalPageVisible(pages.ecodesign, 'settings')).toBe(false)
    expect(isInformationalPageVisible(pages.ecodesign, 'legal_menu')).toBe(true)
  })

  it('falls back to the French content and rejects unsafe external URLs', () => {
    const pages = normalizeInformationalPages({
      pages: {
        accessibility: {
          ...DEFAULT_INFORMATIONAL_PAGES.accessibility,
          mode: 'external',
          external_url: 'javascript:alert(1)',
          content_by_locale: { fr: '# Déclaration' }
        }
      }
    })

    expect(informationalPageLinkProps('accessibility', pages).href).toBe(ACCESSIBILITY_PATH)
    expect(localizedInformationalContent(pages.accessibility, 'en')).toBe('# Déclaration')
  })
})

describe('LegalLinksContext', () => {
  it('lists every legal page on the same canonical paths', () => {
    const links = _createLegalLinksContext(() => informationalLegalPageLinks)
    expect(links.legalMenuLinks.map((link) => link.href)).toEqual([
      TERMS_PATH,
      PRIVACY_POLICY_PATH,
      LEGAL_NOTICE_PATH,
      ACCESSIBILITY_PATH,
      ECODESIGN_PATH
    ])
  })

  it('keeps settings links independent from menu visibility', () => {
    const apiLinks = structuredClone(informationalLegalPageLinks)
    apiLinks.ecodesign.visible_in_legal_menu = false
    const links = _createLegalLinksContext(() => apiLinks)

    expect(links.legalMenuLinks.some((link) => link.href.includes('eco-design'))).toBe(false)
    expect(links.settingsMenuLinks.some((link) => link.href.includes('eco-design'))).toBe(true)
  })
})
