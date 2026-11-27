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

  it('keeps a hostile address and site id inside the tracker script', () => {
    const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8')
    const url = `https://stats.test/a'"\\\`</script><script>alert(1)//`
    const id = `1'</script><img src=x onerror=alert(2)>`
    const page = fillMatomoPlaceholder(template, { url, id }, true)

    expect(page).not.toContain('<script>alert(1)')
    expect(page).not.toContain('<img src=x')
    const script = page.match(/<!-- Matomo -->\s*<script nonce="[^"]*">([\s\S]*?)<\/script>/)![1]
    const pushed: unknown[][] = []
    const scripts = [{ parentNode: { insertBefore: () => {} } }]
    const document = {
      createElement: () => ({}),
      getElementsByTagName: () => scripts
    }
    const window: { _paq?: unknown } = {}
    new Function('window', 'document', 'location', script)(window, document, { pathname: '/' })
    pushed.push(...(window._paq as unknown[][]))
    expect(pushed).toContainEqual(['setTrackerUrl', `${url}/matomo.php`])
    expect(pushed).toContainEqual(['setSiteId', id])
  })

  it('leaves placeholder names in the address as they are', () => {
    const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8')
    const url = 'https://stats.test/%matomo_id_js%/%nonce%'
    const page = fillMatomoPlaceholder(template, { url, id: '1' }, true)

    expect(page).toContain(`var u = ${JSON.stringify(url)} + '/'`)
    expect(page).toContain(`src="${url}/matomo.php?idsite=1&amp;rec=1"`)
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
  const env = { MATOMO_URL: 'https://stats.test', MATOMO_ID: '1' }
  const own = { matomo_url: 'https://own-stats.test/matomo', matomo_site_id: '7' }

  it('follows the Matomo address and site id the server was given', () => {
    expect(measurementInUse({ matomo_enabled: null, ...own }, env)).toEqual({
      url: 'https://stats.test',
      id: '1'
    })
  })

  it.each([
    ['no address', { MATOMO_ID: '1' }],
    ['no site id', { MATOMO_URL: 'https://stats.test', MATOMO_ID: '' }],
    ['neither', {}]
  ])('is none when the server has %s', (_case, env) => {
    expect(measurementInUse({ matomo_enabled: null, ...own }, env)).toBeNull()
  })

  it('is none when the admin turned it off, whatever the server says', () => {
    expect(measurementInUse({ matomo_enabled: false, ...own }, env)).toBeNull()
  })

  it('follows the server until the admin setting has been read once', () => {
    expect(measurementInUse(null, env)).toEqual({ url: 'https://stats.test', id: '1' })
  })

  it.each([
    ['the server has its own', env],
    ['the server has none', {}]
  ])('measures with the admin’s address and site id when on and %s', (_case, env) => {
    expect(measurementInUse({ matomo_enabled: true, ...own }, env)).toEqual({
      url: 'https://own-stats.test/matomo',
      id: '7'
    })
  })
})
