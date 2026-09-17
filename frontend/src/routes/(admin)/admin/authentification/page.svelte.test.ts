import type { AppSettingsPublic } from '$lib/generated/admin'
import { render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn(), getUrl: vi.fn((path: string) => path) }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

const base: AppSettingsPublic = {
  auth_access_policy: 'anonymous_first',
  auth_domain_allowlist: [],
  auth_methods: ['email_code'],
  votes_objective: 300000,
  platform_name: 'Compar:IA',
  primary_color_light: '#6464F3',
  primary_color_dark: '#9898F8',
  secondary_color_light: '#FF9575',
  secondary_color_dark: '#FFCC00',
  homepage_url: null,
  analysis_endpoint_id: null,
  analysis_model: null,
  publish_frequency: 'off',
  publish_hour: 3,
  publish_timezone: 'UTC',
  has_custom_logo: false,
  enabled_locales: ['fr'],
  default_locale: 'fr',
  oidc_issuer: null,
  oidc_client_id: null,
  oidc_has_client_secret: false,
  oidc_scopes: ['openid', 'email'],
  oidc_button_label: null,
  oidc_has_button_logo: false,
  oidc_button_logo_content_type: null,
  updated_at: '2026-01-01T00:00:00'
}

async function renderPage(settings: AppSettingsPublic) {
  const { api } = await import('$lib/fastapi-client')
  vi.mocked(api.request).mockResolvedValueOnce(settings)
  const result = render(Page)
  await waitFor(() =>
    expect(result.container.querySelector('#settings-method-email-code')).toBeInTheDocument()
  )
  return result
}

describe('admin authentification page — auth methods', () => {
  it('checks email_code when server returns it as the only method', async () => {
    const { container } = await renderPage({ ...base, auth_methods: ['email_code'] })
    expect(container.querySelector<HTMLInputElement>('#settings-method-email-code')?.checked).toBe(
      true
    )
    expect(container.querySelector<HTMLInputElement>('#settings-method-oidc')?.checked).toBe(false)
  })

  it('checks both methods when server returns both', async () => {
    const { container } = await renderPage({ ...base, auth_methods: ['email_code', 'oidc'] })
    expect(container.querySelector<HTMLInputElement>('#settings-method-email-code')?.checked).toBe(
      true
    )
    expect(container.querySelector<HTMLInputElement>('#settings-method-oidc')?.checked).toBe(true)
  })
})

describe('admin authentification page — OIDC section visibility', () => {
  it('hides the OIDC config section when oidc is not an auth method', async () => {
    const { container } = await renderPage({ ...base, auth_methods: ['email_code'] })
    expect(container.querySelector('#settings-oidc-config')).not.toBeInTheDocument()
  })

  it('shows the OIDC config section when oidc is among the auth methods', async () => {
    const { container } = await renderPage({ ...base, auth_methods: ['oidc'] })
    expect(container.querySelector('#settings-oidc-config')).toBeInTheDocument()
  })
})

describe('admin authentification page — client secret write-only', () => {
  it('shows the secret field empty when no secret is stored', async () => {
    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: false
    })
    const field = container.querySelector<HTMLInputElement>('#settings-oidc-secret')
    expect(field).toBeInTheDocument()
    expect(field?.value).toBe('')
  })

  it('masks the secret when one is already stored, without pre-filling the field', async () => {
    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true
    })
    expect(container.querySelector('#settings-oidc-secret')).not.toBeInTheDocument()
    expect(container.querySelector('#settings-oidc-secret-masked')).toBeInTheDocument()
    expect(
      container.querySelector<HTMLButtonElement>('#settings-oidc-secret-replace')
    ).toBeInTheDocument()
  })
})

describe('admin authentification page — client-side validation', () => {
  it('requires issuer and client_id when OIDC is enabled on submit', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()

    const { container } = await renderPage({ ...base, auth_methods: ['oidc'] })

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    expect(api.request).not.toHaveBeenCalledWith(
      '/admin/settings',
      expect.objectContaining({ method: 'PATCH' })
    )
    expect(container.querySelector('#input-settings-oidc-issuer-messages')).toBeInTheDocument()
    expect(container.querySelector('#input-settings-oidc-client-id-messages')).toBeInTheDocument()
  })

  it('requires client secret when OIDC is enabled and none is stored', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()

    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: false,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client'
    })

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    expect(api.request).not.toHaveBeenCalledWith(
      '/admin/settings',
      expect.objectContaining({ method: 'PATCH' })
    )
    expect(container.querySelector('#settings-oidc-secret-error')).toBeInTheDocument()
  })

  it('does not require client secret when OIDC is enabled and one is already stored', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true
    })

    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client'
    })

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/settings',
      expect.objectContaining({ method: 'PATCH' })
    )
  })
})

describe('admin authentification page — save payload', () => {
  it('includes auth_methods and OIDC fields in the PATCH body', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true
    })

    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: false,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client'
    })

    const secretField = container.querySelector<HTMLInputElement>('#settings-oidc-secret')!
    secretField.value = 'my-secret'
    secretField.dispatchEvent(new Event('input', { bubbles: true }))

    const scopesField = container.querySelector<HTMLInputElement>('#settings-oidc-scopes')!
    scopesField.value = 'openid email profile'
    scopesField.dispatchEvent(new Event('input', { bubbles: true }))

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/settings',
      expect.objectContaining({ method: 'PATCH' })
    )
    // calls[0] is the GET from onMount; calls[1] is the PATCH from save
    const body = JSON.parse(vi.mocked(api.request).mock.calls[1][1]!.body as string)
    expect(body.auth_methods).toEqual(['oidc'])
    expect(body.oidc_issuer).toBe('https://auth.example.fr')
    expect(body.oidc_client_id).toBe('my-client')
    expect(body.oidc_client_secret).toBe('my-secret')
    expect(body.oidc_scopes).toEqual(['openid', 'email', 'profile'])
  })

  it('omits oidc_client_secret from the body when no new secret is entered', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true
    })

    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client'
    })

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    // calls[0] is the GET from onMount; calls[1] is the PATCH from save
    const body = JSON.parse(vi.mocked(api.request).mock.calls[1][1]!.body as string)
    expect('oidc_client_secret' in body).toBe(false)
  })
})
