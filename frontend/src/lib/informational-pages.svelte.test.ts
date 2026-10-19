import { describe, expect, it } from 'vitest'
import {
  ACCESSIBILITY_PATH,
  ECODESIGN_PATH,
  LEGAL_NOTICE_PATH,
  PRIVACY_POLICY_PATH,
  TERMS_PATH
} from './consent'
import { _createLegalLinksContext } from './informational-pages.svelte'
import { informationalLegalPageLinks } from './testing/mock-data'

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

    expect(links.legalMenuLinks.some((link) => link.href.includes('ecodesign'))).toBe(false)
    expect(links.settingsMenuLinks.some((link) => link.href.includes('ecodesign'))).toBe(true)
  })
})
