import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('Matomo tracker', () => {
  it('keeps an opt-out from one page to the next', () => {
    const page = readFileSync(new URL('./app.html', import.meta.url), 'utf8')

    // setConsentGiven deletes the mtm_consent_removed cookie that the
    // privacy page's opt-out writes, so the visitor would be tracked again.
    expect(page).toContain("_paq.push(['trackPageView'])")
    expect(page).not.toContain('setConsentGiven')
  })

  // The inline script of the page, as the browser would run it once the server
  // has replaced %instance_cookie_path% with the Instance path.
  function trackedCalls(pathname: string, instanceCookiePath: string) {
    const page = readFileSync(new URL('./app.html', import.meta.url), 'utf8')
    const script = page
      .split('<script nonce="%sveltekit.nonce%">')
      .find((chunk) => chunk.includes('_paq'))!
      .split('</script>')[0]
      .replaceAll('%instance_cookie_path%', instanceCookiePath)
      .replaceAll('%matomo_url%', 'https://matomo.test')
      .replaceAll('%matomo_id%', '1')
    const calls: unknown[][] = []
    const window = { _paq: { push: (call: unknown[]) => calls.push(call) } }
    const document = {
      createElement: () => ({}),
      getElementsByTagName: () => [{ parentNode: { insertBefore: () => {} } }]
    }
    const location = { pathname, origin: 'https://arene.test' }
    new Function('window', 'document', 'location', script)(window, document, location)
    return calls
  }

  it('keeps the invite token off Matomo, with or without an Instance path', () => {
    expect(trackedCalls('/invite/secret', '/')).toContainEqual([
      'setCustomUrl',
      'https://arene.test/invite/<redacted>'
    ])
    expect(trackedCalls('/fr/invite/secret', '/fr')).toContainEqual([
      'setCustomUrl',
      'https://arene.test/fr/invite/<redacted>'
    ])
  })

  it('reports the other pages as they are', () => {
    expect(trackedCalls('/fr/models', '/fr').some(([name]) => name === 'setCustomUrl')).toBe(false)
  })
})
