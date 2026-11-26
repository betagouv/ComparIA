import { describe, expect, it } from 'vitest'
import da from '../../locales/messages/da.json'

// The footer link and the page it opens must name a document the same way.
describe('Danish legal labels', () => {
  it('calls the terms the same thing in the link, the page title and the tab title', () => {
    expect(da.general.terms.title).toBe(da.consent.links.terms)
    expect(da.seo.titles.terms).toBe(da.consent.links.terms)
  })

  it('calls the privacy policy the same thing in the link, the page title and the tab title', () => {
    expect(da.general.privacy_policy.title).toBe(da.consent.links.privacy_policy)
    expect(da.seo.titles.privacy_policy).toBe(da.consent.links.privacy_policy)
  })

  it('uses one word for the terms everywhere', () => {
    expect(JSON.stringify(da)).not.toMatch(/brugsbetingelse/i)
    expect(JSON.stringify(da)).not.toMatch(/fortrolighedspolitik/i)
  })

  it('no longer says every substitute document is French', () => {
    expect(da.general.document.otherLanguage).toContain('{language}')
    expect(da.general.document.otherLanguage).not.toMatch(/fransk/)
  })
})
