import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import AdminError from './(admin)/+error.svelte'
import RootError from './+error.svelte'
import Login from './login/+page.svelte'

// The Instance is served under /fr: every link and image an Instance renders
// has to carry the prefix.
const mocks = vi.hoisted(() => ({
  pageState: { status: 404, url: new URL('http://localhost/fr/login') },
  authContext: {
    user: null,
    config: {
      access_policy: 'sign_in_required',
      methods: ['oidc'] as string[],
      oidc_enabled: true,
      oidc_button_label: 'Se connecter',
      oidc_has_button_logo: false,
      platform_name: 'Compar:IA',
      has_custom_logo: false
    }
  }
}))

vi.mock('$app/navigation', () => ({ goto: vi.fn(), replaceState: vi.fn() }))
vi.mock('$app/paths', () => ({
  resolve: (path: string) => `/fr${path}`,
  asset: (path: string) => `/fr${path}`,
  match: vi.fn()
}))
vi.mock('$app/state', () => ({ page: mocks.pageState }))
vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => mocks.authContext }))
vi.mock('$lib/authContext.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/authContext.svelte')>()),
  getPlatformName: () => 'Compar:IA',
  tryGetAuthContext: () => mocks.authContext
}))
vi.mock('$lib/captcha.svelte', () => ({ consumeAltchaToken: () => Promise.resolve('token') }))
vi.mock('$lib/fastapi-client', () => ({
  api: {
    request: vi.fn().mockRejectedValue(new Error('offline')),
    getPublicUrl: (path: string) => path
  }
}))
vi.mock('$lib/i18n/runtime', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/i18n/runtime')>()),
  getLocale: () => 'fr'
}))

describe('links and images under an Instance path', () => {
  it('sends a lost visitor back to the home page of the Instance', () => {
    render(RootError)

    expect(screen.getByRole('link', { name: /accueil/i })).toHaveAttribute('href', '/fr/')
  })

  it('sends a lost administrator back to the admin home of the Instance', () => {
    render(AdminError)

    expect(screen.getByRole('link', { name: /accueil/i })).toHaveAttribute('href', '/fr/admin')
  })

  it('serves the default logo of the sign-in page from the Instance', () => {
    const { container } = render(Login)

    expect(container.querySelector('img[src$="/orgs/comparia.png"]')).toHaveAttribute(
      'src',
      '/fr/orgs/comparia.png'
    )
  })
})
