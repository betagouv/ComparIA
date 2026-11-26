import { beforeEach, describe, expect, it, vi } from 'vitest'

// The Instance is served under /fr: redirects must land on the Instance, and
// the page to come back to after sign-in is kept without the prefix.
const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$app/paths', () => ({ resolve: (path: string) => `/fr${path}` }))
vi.mock('$lib/fastapi-client', () => ({
  api: { request },
  TOTP_SETUP_PATH: '/settings?totp=required'
}))

const { load: adminLayout } = await import('./+layout')
const { load: adminIndex } = await import('./admin/+page.server')
const { load: llmsIndex } = await import('./admin/llms/+page.server')
const { load: activityIndex } = await import('./admin/activite/+page')

async function redirectOf(run: () => unknown) {
  try {
    await run()
  } catch (error) {
    return error as { status: number; location: string }
  }
  throw new Error('expected a redirect')
}

describe('admin redirects under an Instance path', () => {
  beforeEach(() => request.mockReset())

  it('sends a signed-out visitor to the login page of the Instance, remembering the page without the prefix', async () => {
    request.mockResolvedValue({ user: null })

    const redirect = await redirectOf(() =>
      adminLayout({ url: new URL('http://arene.test/fr/admin/utilisateurs'), fetch } as never)
    )

    expect(redirect).toMatchObject({
      status: 302,
      location: '/fr/login?redirect=%2Fadmin%2Futilisateurs'
    })
  })

  it('sends an admin without an authenticator to the enrolment page of the Instance', async () => {
    request.mockResolvedValue({ user: { role: 'admin', totp_enabled: false } })

    const redirect = await redirectOf(() =>
      adminLayout({ url: new URL('http://arene.test/fr/admin'), fetch } as never)
    )

    expect(redirect).toMatchObject({ status: 302, location: '/fr/settings?totp=required' })
  })

  it('sends /admin to the activity pages of the Instance', async () => {
    expect(await redirectOf(() => adminIndex({} as never))).toMatchObject({
      status: 302,
      location: '/fr/admin/activite'
    })
  })

  it('sends /admin/llms to the models list of the Instance', async () => {
    expect(await redirectOf(() => llmsIndex({} as never))).toMatchObject({
      status: 302,
      location: '/fr/admin/llms/llms'
    })
  })

  it('keeps the filters when sending the activity index to its overview', async () => {
    const redirect = await redirectOf(() =>
      activityIndex({ url: new URL('http://arene.test/fr/admin/activite?period=7d') } as never)
    )

    expect(redirect).toMatchObject({
      status: 307,
      location: '/fr/admin/activite/apercu?period=7d'
    })
  })
})
