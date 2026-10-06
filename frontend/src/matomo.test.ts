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
})
