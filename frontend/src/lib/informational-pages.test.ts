import { describe, expect, it } from 'vitest'
import {
  DEFAULT_INFORMATIONAL_PAGES,
  informationalPageHref,
  isInformationalPageVisible,
  localizedInformationalContent,
  normalizeInformationalPages
} from './informational-pages'

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
          external_url: 'https://example.gouv.fr/ecoconception',
          visible_in_settings: false
        }
      }
    })

    expect(informationalPageHref('ecodesign', pages)).toBe('https://example.gouv.fr/ecoconception')
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

    expect(informationalPageHref('accessibility', pages)).toBe('/arene/accessibilite')
    expect(localizedInformationalContent(pages.accessibility, 'en')).toBe('# Déclaration')
  })
})
