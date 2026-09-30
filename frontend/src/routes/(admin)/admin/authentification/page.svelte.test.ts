import type { AppSettingsPublic } from '$lib/generated/admin'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

vi.mock('$lib/fastapi-client', () => ({
  api: {
    request: vi.fn(),
    getUrl: vi.fn((path: string, searchParams?: Record<string, string>) =>
      searchParams ? `${path}?${new URLSearchParams(searchParams)}` : path
    )
  }
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
    expect(container.querySelector('#settings-oidc-secret')).toHaveAttribute('aria-invalid', 'true')
  })

  it('requires openid among the scopes when OIDC is enabled', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()

    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_client_secret: true,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client',
      oidc_scopes: ['email', 'profile']
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
    await waitFor(() =>
      expect(
        container.querySelector('#input-settings-oidc-scopes-messages .fr-message--error')
      ).toBeInTheDocument()
    )
    expect(container.querySelector('#settings-oidc-scopes')).toHaveAttribute('aria-invalid', 'true')
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

  it('keeps the stored OIDC config when OIDC is unticked', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue({ ...base, auth_methods: ['email_code'] })

    const { container } = await renderPage({
      ...base,
      auth_methods: ['email_code', 'oidc'],
      oidc_has_client_secret: true,
      oidc_issuer: 'https://auth.example.fr',
      oidc_client_id: 'my-client',
      oidc_button_label: 'ProConnect'
    })

    await fireEvent.click(container.querySelector<HTMLInputElement>('#settings-method-oidc')!)
    expect(container.querySelector('#settings-oidc-config')).not.toBeInTheDocument()

    container
      .querySelector<HTMLFormElement>('#settings-auth-form')!
      .dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()

    // calls[0] is the GET from onMount; calls[1] is the PATCH from save
    const body = JSON.parse(vi.mocked(api.request).mock.calls[1][1]!.body as string)
    expect(body.auth_methods).toEqual(['email_code'])
    for (const key of [
      'oidc_issuer',
      'oidc_client_id',
      'oidc_client_secret',
      'oidc_scopes',
      'oidc_button_label'
    ]) {
      expect(key in body).toBe(false)
    }
  })
})

describe('admin authentification page — OIDC button logo', () => {
  it('previews the logo from the public endpoint', async () => {
    const { container } = await renderPage({
      ...base,
      auth_methods: ['oidc'],
      oidc_has_button_logo: true
    })
    const preview = container.querySelector<HTMLImageElement>('#settings-oidc-config img')
    expect(preview?.getAttribute('src')).toBe('/auth/config/oidc/logo?v=0')
  })
})

describe('admin authentification page — OIDC connection test', () => {
  const configured: AppSettingsPublic = {
    ...base,
    auth_methods: ['email_code', 'oidc'],
    oidc_has_client_secret: true,
    oidc_issuer: 'https://auth.example.fr',
    oidc_client_id: 'my-client'
  }
  const passed = { passed: true, reason: null, tested_at: '2026-01-02T10:00:00' }

  function button(container: HTMLElement) {
    return container.querySelector<HTMLButtonElement>('#settings-oidc-test')!
  }

  it('runs the test and shows that it passed', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    const { container, getByRole } = await renderPage(configured)
    vi.mocked(api.request).mockResolvedValueOnce(passed)

    await fireEvent.click(button(container))

    await waitFor(() => expect(getByRole('status').textContent).toContain('Connexion réussie'))
    expect(api.request).toHaveBeenCalledWith(
      '/admin/settings/oidc/test',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('shows a readable reason when the test fails', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    const { container, getByRole } = await renderPage(configured)
    vi.mocked(api.request).mockResolvedValueOnce({
      passed: false,
      reason: 'issuer_mismatch',
      tested_at: '2026-01-02T10:00:00'
    })

    await fireEvent.click(button(container))

    await waitFor(() => expect(getByRole('status').textContent).toContain('émetteur'))
    expect(getByRole('status').textContent).not.toContain('issuer_mismatch')
  })

  it('shows the stored result next to the config on load', async () => {
    const { getByRole } = await renderPage({ ...configured, oidc_connection_test: passed })
    expect(getByRole('status').textContent).toContain('Connexion réussie')
  })

  it('asks to save before testing when the provider fields were edited', async () => {
    const { container } = await renderPage(configured)
    const issuer = container.querySelector<HTMLInputElement>('#settings-oidc-issuer')!
    await fireEvent.input(issuer, { target: { value: 'https://other.example.fr' } })

    expect(button(container).disabled).toBe(true)
    expect(container.querySelector('#settings-oidc-test-hint')).toBeInTheDocument()
  })

  it('keeps email_code locked until a test passed on the current config', async () => {
    const { container } = await renderPage(configured)
    const emailCode = container.querySelector<HTMLInputElement>('#settings-method-email-code')!
    expect(emailCode.disabled).toBe(true)
    expect(container.querySelector('#settings-method-email-code-help')).toBeInTheDocument()
  })

  it('unlocks email_code after a passing test', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    const { container } = await renderPage(configured)
    vi.mocked(api.request).mockResolvedValueOnce(passed)

    await fireEvent.click(button(container))

    await waitFor(() =>
      expect(
        container.querySelector<HTMLInputElement>('#settings-method-email-code')!.disabled
      ).toBe(false)
    )
  })

  it('unlocks email_code when the server reports a passing test on load', async () => {
    const { container } = await renderPage({ ...configured, oidc_connection_test: passed })
    expect(container.querySelector<HTMLInputElement>('#settings-method-email-code')!.disabled).toBe(
      false
    )
  })

  it('does not lock email_code on an instance without OIDC', async () => {
    const { container } = await renderPage({ ...base, auth_methods: ['email_code'] })
    expect(container.querySelector<HTMLInputElement>('#settings-method-email-code')!.disabled).toBe(
      false
    )
  })

  it('locks email_code again once the provider fields are edited', async () => {
    const { container } = await renderPage({ ...configured, oidc_connection_test: passed })
    await fireEvent.input(container.querySelector<HTMLInputElement>('#settings-oidc-client-id')!, {
      target: { value: 'another-client' }
    })
    expect(container.querySelector<HTMLInputElement>('#settings-method-email-code')!.disabled).toBe(
      true
    )
  })
})
