import { describe, expect, it, vi } from 'vitest'
import { signInMethods } from './signInMethods'

vi.mock('$lib/fastapi-client', () => ({
  api: { getUrl: (path: string) => path }
}))

describe('signInMethods', () => {
  it('offers the email code alone until the config says otherwise', () => {
    const methods = signInMethods(undefined)
    expect(methods.emailEnabled).toBe(true)
    expect(methods.oidcEnabled).toBe(false)
    expect(methods.bothMethods).toBe(false)
    expect(methods.tabs.map((tab) => tab.id)).toEqual(['email'])
  })

  it('offers one tab per enabled method', () => {
    const methods = signInMethods({ methods: ['email_code', 'oidc'], oidc_enabled: true })
    expect(methods.bothMethods).toBe(true)
    expect(methods.tabs.map((tab) => tab.id)).toEqual(['email', 'sso'])
  })

  it('leaves out the email code on an SSO-only instance', () => {
    const methods = signInMethods({ methods: ['oidc'], oidc_enabled: true })
    expect(methods.emailEnabled).toBe(false)
    expect(methods.bothMethods).toBe(false)
    expect(methods.tabs.map((tab) => tab.id)).toEqual(['sso'])
  })

  it('hides SSO when the server says it cannot work', () => {
    const methods = signInMethods({ methods: ['email_code', 'oidc'], oidc_enabled: false })
    expect(methods.oidcEnabled).toBe(false)
    expect(methods.tabs.map((tab) => tab.id)).toEqual(['email'])
  })

  it('takes the label and the logo from the config', () => {
    const custom = signInMethods({ oidc_button_label: 'ProConnect', oidc_has_button_logo: true })
    expect(custom.oidcLabel).toBe('ProConnect')
    expect(custom.oidcLogoUrl).toBe('/auth/config/oidc/logo')
    const fallback = signInMethods({ oidc_button_label: null, oidc_has_button_logo: false })
    expect(fallback.oidcLabel).toContain('fournisseur d’identité')
    expect(fallback.oidcLogoUrl).toBeNull()
  })
})
