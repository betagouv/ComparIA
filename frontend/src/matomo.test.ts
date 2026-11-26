import { fillMatomoPlaceholder, measurementInUse } from '$lib/matomo'
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

  it('leaves the page free of Matomo when nothing is measured', () => {
    const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8')

    for (const load of [true, false]) {
      const page = fillMatomoPlaceholder(template, null, load)
      expect(page).not.toContain('_paq')
      expect(page).not.toContain('matomo-config')
      expect(page).not.toContain('<!-- matomo')
    }
  })
})

describe('measurement in use', () => {
  it('follows the Matomo address and site id the server was given', () => {
    expect(measurementInUse({ MATOMO_URL: 'https://stats.test', MATOMO_ID: '1' })).toEqual({
      url: 'https://stats.test',
      id: '1'
    })
  })

  it.each([
    ['no address', { MATOMO_ID: '1' }],
    ['no site id', { MATOMO_URL: 'https://stats.test', MATOMO_ID: '' }],
    ['neither', {}]
  ])('is none when the server has %s', (_case, env) => {
    expect(measurementInUse(env)).toBeNull()
  })
})
