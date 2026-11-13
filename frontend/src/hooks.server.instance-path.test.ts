import { beforeEach, describe, expect, it, vi } from 'vitest'

// The Instance is served under /fr: SvelteKit hands the hooks URLs that carry
// the prefix, and `resolve` puts it back on the paths we redirect to.
const { request, privateEnv } = vi.hoisted(() => ({
  request: vi.fn(),
  privateEnv: { AUTH_ACCESS_POLICY: 'sign_in_required' } as Record<string, string>
}))

vi.mock('$app/paths', () => ({
  base: '/fr',
  resolve: (path: string) => `/fr${path}`
}))
vi.mock('$env/dynamic/private', () => ({ env: privateEnv }))
vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/fastapi-client', () => ({
  api: { request },
  UnauthorizedError: class {},
  TOTP_SETUP_PATH: '/settings?totp=required',
  isTotpSetupRequired: () => false
}))
vi.mock('$lib/localeCookie', () => ({}))
vi.mock('$lib/i18n/runtime', () => ({ defineCustomServerStrategy: () => {}, cookieMaxAge: 100 }))
vi.mock('$lib/i18n/server', () => ({
  paraglideMiddleware: (
    request: Request,
    run: (args: { request: Request; locale: string }) => unknown
  ) => run({ request, locale: 'da' })
}))
vi.mock('$lib/logger.server', () => ({ logger: { error: () => {}, info: () => {} } }))
const { counted } = vi.hoisted(() => ({ counted: vi.fn() }))
vi.mock('$lib/metrics', () => ({
  httpRequestCounter: { inc: counted },
  httpRequestDuration: { observe: () => {} }
}))

const { authWallHandle, maintenanceHandle, metricsHandle, paraglideHandle } =
  await import('./hooks.server')

const resolve = vi.fn(async () => new Response('page'))

function eventAt(pathname: string, cookie?: string) {
  return {
    url: new URL(`http://arene.test${pathname}`),
    request: new Request(`http://arene.test${pathname}`),
    route: { id: null },
    cookies: {
      get: (name: string) => (name === 'auth_session' ? cookie : undefined),
      delete: () => {}
    },
    fetch
  } as never
}

async function redirectedFrom(run: () => Response | Promise<Response>) {
  try {
    await run()
  } catch (error) {
    return error as { status: number; location: string }
  }
}

describe('sign-in wall under an Instance path', () => {
  beforeEach(() => {
    request.mockReset()
    resolve.mockClear()
    privateEnv.AUTH_ACCESS_POLICY = 'sign_in_required'
  })

  it('sends a visitor with no cookie to the login page of the Instance, and remembers the page without the prefix', async () => {
    const redirect = await redirectedFrom(() =>
      authWallHandle({ event: eventAt('/fr/statistics'), resolve } as never)
    )

    expect(redirect?.status).toBe(302)
    expect(redirect?.location).toBe('/fr/login?redirect=%2Fstatistics')
  })

  it('lets the login page of the Instance through', async () => {
    const response = await authWallHandle({ event: eventAt('/fr/login'), resolve } as never)

    expect(await response.text()).toBe('page')
  })

  it('lets the built assets of the Instance through', async () => {
    const response = await authWallHandle({ event: eventAt('/fr/_app/x.js'), resolve } as never)

    expect(await response.text()).toBe('page')
  })

  it('lets the maintenance page of the Instance through', async () => {
    const response = await authWallHandle({ event: eventAt('/fr/maintenance'), resolve } as never)

    expect(await response.text()).toBe('page')
  })
})

describe('maintenance mode under an Instance path', () => {
  beforeEach(() => {
    privateEnv.AUTH_ACCESS_POLICY = 'open'
    request.mockReset()
  })

  it('sends visitors to the maintenance page of the Instance', async () => {
    request.mockResolvedValue({ enabled: true })

    const redirect = await redirectedFrom(() =>
      maintenanceHandle({ event: eventAt('/fr/statistics'), resolve } as never)
    )

    expect(redirect?.status).toBe(307)
    expect(redirect?.location).toBe('/fr/maintenance')
  })

  it('does not loop on the maintenance page of the Instance', async () => {
    request.mockResolvedValue({ enabled: true })

    const redirect = await redirectedFrom(() =>
      maintenanceHandle({ event: eventAt('/fr/maintenance'), resolve } as never)
    )

    expect(redirect).toBeUndefined()
  })
})

describe('metrics under an Instance path', () => {
  beforeEach(() => counted.mockClear())

  it('does not count the scrape of the metrics endpoint of the Instance', async () => {
    await metricsHandle({ event: eventAt('/fr/metrics'), resolve } as never)

    expect(counted).not.toHaveBeenCalled()
  })

  it('counts other requests', async () => {
    await metricsHandle({ event: eventAt('/fr/statistics'), resolve } as never)

    expect(counted).toHaveBeenCalledOnce()
  })
})

describe('cookies under an Instance path', () => {
  function cookieJar() {
    return { set: vi.fn(), delete: vi.fn(), get: () => undefined }
  }

  it('sets the locale cookie on the Instance path, so that another Instance does not see it', async () => {
    const cookies = cookieJar()

    await paraglideHandle({
      event: { ...(eventAt('/fr/') as object), cookies },
      resolve
    } as never)

    expect(cookies.set).toHaveBeenCalledWith(
      'PARAGLIDE_LOCALE',
      'da',
      expect.objectContaining({ path: '/fr' })
    )
  })

  it('gives the inline script of the page the Instance path as cookie path for scheme and theme', async () => {
    const render = vi.fn(
      async (
        _event: unknown,
        options: { transformPageChunk: (chunk: { html: string }) => string | Promise<string> }
      ) => {
        const html = await options.transformPageChunk({
          html: "document.cookie = 'x=1; path=%instance_cookie_path%'"
        })
        return new Response(html)
      }
    )

    const response = await paraglideHandle({
      event: { ...(eventAt('/fr/') as object), cookies: cookieJar() },
      resolve: render
    } as never)

    expect(await response.text()).toBe("document.cookie = 'x=1; path=/fr'")
  })

  it('deletes the session cookie on the Instance path when the session is gone', async () => {
    const cookies = { get: () => 'stale', delete: vi.fn() }
    privateEnv.AUTH_ACCESS_POLICY = 'sign_in_required'
    request.mockResolvedValue({ user: null })

    await redirectedFrom(() =>
      authWallHandle({
        event: { ...(eventAt('/fr/statistics') as object), cookies },
        resolve
      } as never)
    )

    expect(cookies.delete).toHaveBeenCalledWith('auth_session', { path: '/fr' })
  })
})
