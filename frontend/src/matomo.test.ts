import { fillMatomoPlaceholder } from '$lib/matomo'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('Matomo tracker', () => {
  it('keeps an opt-out from one page to the next', () => {
    const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8')
    const page = fillMatomoPlaceholder(template, { url: 'https://stats.test', id: '1' }, true)

    // setConsentGiven deletes the mtm_consent_removed cookie that the
    // privacy page's opt-out writes, so the visitor would be tracked again.
    expect(page).toContain("_paq.push(['trackPageView'])")
    expect(page).not.toContain('setConsentGiven')
  })

  it.each([
    ['no address', { url: '', id: '1' }],
    ['no site id', { url: 'https://stats.test', id: '' }]
  ])('leaves the page free of Matomo when the instance has %s', (_case, config) => {
    const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8')

    for (const load of [true, false]) {
      const page = fillMatomoPlaceholder(template, config, load)
      expect(page).not.toContain('_paq')
      expect(page).not.toContain('matomo-config')
      expect(page).not.toContain('<!-- matomo')
    }
  })
})
