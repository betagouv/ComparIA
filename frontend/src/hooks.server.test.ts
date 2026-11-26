import { readFileSync } from 'node:fs'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { request, countRequest, privateEnv } = vi.hoisted(() => ({
  request: vi.fn(),
  countRequest: vi.fn(),
  privateEnv: {
    AUTH_ACCESS_POLICY: 'sign_in_required',
    MATOMO_ID: '42',
    MATOMO_URL: 'https://stats.test'
  } as Record<string, string>
}))

vi.mock('$env/dynamic/private', () => ({ env: privateEnv }))
vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/fastapi-client', () => ({ api: { request }, UnauthorizedError: class {} }))
vi.mock('$lib/i18n/runtime', () => ({ cookieMaxAge: 1000, defineCustomServerStrategy: () => {} }))
vi.mock('$lib/i18n/server', () => ({
  paraglideMiddleware: (
    request: Request,
    resolve: (args: { request: Request; locale: string }) => unknown
  ) => resolve({ request, locale: 'fr' })
}))
vi.mock('$lib/logger.server', () => ({ logger: { error: () => {}, info: () => {} } }))
vi.mock('$lib/metrics', () => ({
  httpRequestCounter: { inc: countRequest },
  httpRequestDuration: { observe: () => {} }
}))

const {
  authWallHandle,
  cookieBannerHandle,
  handleFetch,
  matomoHandle,
  metricsHandle,
  paraglideHandle,
  securityHeadersHandle
} = await import('./hooks.server')

const resolve = vi.fn(async () => new Response('page'))

// Runs the switch handle the way the hook sequence does, a minute after the
// last call so the config cache is always stale.
let clock = Date.now()
async function localsFor(switchOn: boolean, jar: Record<string, string | undefined> = {}) {
  clock += 60_000
  vi.setSystemTime(clock)
  request.mockResolvedValue({ cookie_banner_enabled: switchOn })
  const event = { locals: {} as App.Locals, cookies: { get: (name: string) => jar[name] } }
  await cookieBannerHandle({ event, resolve: async () => new Response() } as never)
  return event.locals
}

function eventWith(cookie?: string, anonymousSession?: string) {
  const deleted: string[] = []
  const jar: Record<string, string | undefined> = {
    auth_session: cookie,
    anonymous_session: anonymousSession
  }
  return {
    deleted,
    event: {
      url: new URL('http://arene.test/statistics'),
      cookies: {
        get: (name: string) => jar[name],
        delete: (name: string) => deleted.push(name)
      },
      fetch
    } as never
  }
}

async function wall(cookie?: string) {
  const { event, deleted } = eventWith(cookie)
  try {
    const response = await authWallHandle({ event, resolve } as never)
    return { response, deleted }
  } catch (error) {
    return { redirect: error as { status: number; location: string }, deleted }
  }
}

describe('sign-in wall', () => {
  beforeEach(() => {
    request.mockReset()
    resolve.mockClear()
    privateEnv.AUTH_ACCESS_POLICY = 'sign_in_required'
  })

  it('sends a visitor with no cookie to the sign-in page', async () => {
    const { redirect } = await wall()

    expect(redirect?.status).toBe(302)
    expect(redirect?.location).toBe('/login?redirect=%2Fstatistics')
    expect(request).not.toHaveBeenCalled()
  })

  it('turns away a cookie the backend does not know, and drops it', async () => {
    request.mockResolvedValue({ user: null })

    const { redirect, deleted } = await wall('forged')

    expect(redirect?.status).toBe(302)
    expect(deleted).toEqual(['auth_session'])
    expect(resolve).not.toHaveBeenCalled()
  })

  it('passes the cookie on to the backend, which answers on another host', async () => {
    request.mockResolvedValue({ user: { email: 'a@example.test' } })

    await wall('real-session')

    expect(request).toHaveBeenCalledWith('/auth/me', {
      fetch: expect.anything(),
      headers: { cookie: 'auth_session=real-session' }
    })
    expect(resolve).toHaveBeenCalled()
  })

  it('lets the page through when the check itself fails', async () => {
    request.mockRejectedValue(new Error('backend down'))

    const { response } = await wall('real-session')

    expect(await response?.text()).toBe('page')
  })

  it('checks nothing when the instance is open to everyone', async () => {
    privateEnv.AUTH_ACCESS_POLICY = 'anonymous_first'

    await wall()

    expect(request).not.toHaveBeenCalled()
    expect(resolve).toHaveBeenCalled()
  })
})

describe('server-side API requests', () => {
  it('forwards the auth session to the backend during SSR', async () => {
    const backendFetch = vi.fn(
      async (request: Request) => new Response(request.headers.get('cookie'))
    )
    const request = new Request('http://localhost:8001/api/admin/llms/data')

    const response = await handleFetch({
      event: eventWith('real-session').event,
      request,
      fetch: backendFetch
    } as never)

    expect(await response.text()).toBe('auth_session=real-session')
  })

  it('forwards the anonymous session so a signed-out visitor keeps their identity', async () => {
    const backendFetch = vi.fn(
      async (request: Request) => new Response(request.headers.get('cookie'))
    )
    const request = new Request('http://localhost:8001/api/survey/questions')

    const response = await handleFetch({
      event: eventWith(undefined, 'anon-token').event,
      request,
      fetch: backendFetch
    } as never)

    expect(await response.text()).toBe('anonymous_session=anon-token')
  })

  it('does not leak the auth session to unrelated origins', async () => {
    const backendFetch = vi.fn(
      async (request: Request) => new Response(request.headers.get('cookie'))
    )
    const request = new Request('https://unrelated.example/api/admin/llms/data')

    const response = await handleFetch({
      event: eventWith('real-session').event,
      request,
      fetch: backendFetch
    } as never)

    expect(await response.text()).toBe('')
  })
})

describe('cookie banner switch on a cold process', () => {
  it('leaves Matomo out and the banner closed when the switch cannot be read', async () => {
    vi.resetModules()
    const fresh = await import('./hooks.server')
    request.mockRejectedValue(new Error('backend down'))
    const event = { locals: {} as App.Locals, cookies: { get: () => undefined } }
    await fresh.cookieBannerHandle({ event, resolve } as never)

    expect(event.locals.cookieBannerEnabled).toBeNull()
    expect(event.locals.measurement).toEqual({ url: 'https://stats.test', id: '42' })
    expect(event.locals.cookieConsent).toMatchObject({ showBanner: false, loadMeasurement: false })
  })
})

describe('cookie banner switch', () => {
  async function bannerEnabled() {
    const event = { locals: {} as App.Locals, cookies: { get: () => undefined } }
    await cookieBannerHandle({ event, resolve } as never)
    return event.locals.cookieBannerEnabled
  }

  beforeEach(() => {
    request.mockReset()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reads the switch from the instance config, once per cache window', async () => {
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    request.mockResolvedValue({ cookie_banner_enabled: false })
    expect(await bannerEnabled()).toBe(false)

    request.mockResolvedValue({ cookie_banner_enabled: true })
    expect(await bannerEnabled()).toBe(false)
    expect(request).toHaveBeenCalledTimes(1)

    vi.setSystemTime(new Date('2026-01-01T00:01:00Z'))
    expect(await bannerEnabled()).toBe(true)
    expect(request).toHaveBeenCalledWith('/auth/config')
  })

  it('keeps the last known switch when the backend is down', async () => {
    vi.setSystemTime(new Date('2026-01-01T00:02:00Z'))
    request.mockResolvedValue({ cookie_banner_enabled: true })
    expect(await bannerEnabled()).toBe(true)

    vi.setSystemTime(new Date('2026-01-01T00:03:00Z'))
    request.mockRejectedValue(new Error('backend down'))
    expect(await bannerEnabled()).toBe(true)
  })

  it('decides the consent once for the rest of the request', async () => {
    const locals = await localsFor(true, {
      comparia_cookie_consent: `1.1.${Math.floor(Date.now() / 1000)}`
    })

    expect(locals.cookieConsent).toEqual({ showBanner: false, loadMeasurement: true })
  })
})

describe('request metrics', () => {
  async function count(path: string, routeId: string | null) {
    countRequest.mockReset()
    const event = {
      url: new URL(`http://arene.test${path}`),
      route: { id: routeId },
      request: new Request(`http://arene.test${path}`)
    } as never
    await metricsHandle({ event, resolve } as never)
    return countRequest.mock.calls[0][0]
  }

  it('labels a request with its route, not its path', async () => {
    expect(await count('/invite/abc123', '/invite/[token]')).toMatchObject({
      route: '/invite/[token]'
    })
  })

  it('puts every unmatched path under one label', async () => {
    expect(await count('/x/random-1', null)).toMatchObject({ route: 'unmatched' })
    expect(await count('/invite/abc123/x', null)).toMatchObject({ route: 'unmatched' })
  })
})

describe('audience measurement', () => {
  // What SvelteKit hands to transformPageChunk: the template with its own
  // placeholders already filled in.
  const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8').replaceAll(
    '%sveltekit.nonce%',
    'n0nce'
  )

  beforeEach(() => vi.useFakeTimers({ toFake: ['Date'] }))
  afterEach(() => vi.useRealTimers())

  async function render(switchOn: boolean, consent?: string) {
    const event = { locals: await localsFor(switchOn, { comparia_cookie_consent: consent }) }
    let html = ''
    await matomoHandle({
      event,
      resolve: async (
        _event: unknown,
        opts?: { transformPageChunk?: (input: { html: string; done: boolean }) => string }
      ) => {
        html = opts?.transformPageChunk?.({ html: template, done: true }) ?? template
        return new Response(html)
      }
    } as never)
    return html
  }

  const now = Math.floor(Date.now() / 1000)

  it('loads Matomo for everyone when the banner is off', async () => {
    const html = await render(false)

    expect(html).toContain('<script nonce="n0nce">\n      var _paq')
    expect(html).toContain("_paq.push(['trackPageView'])")
    expect(html).toContain("var u = 'https://stats.test/'")
    expect(html).toContain("_paq.push(['setSiteId', '42'])")
    expect(html).toContain('src="https://stats.test/matomo.php?idsite=42&amp;rec=1"')
    expect(html).toContain("location.origin + '/invite/<redacted>'")
  })

  it('leaves Matomo out until the visitor answers', async () => {
    const html = await render(true)

    expect(html).not.toContain('_paq')
    expect(html).not.toContain('matomo.php')
  })

  it('loads Matomo once the visitor accepts audience measurement', async () => {
    const html = await render(true, `1.1.${now}`)

    expect(html).toContain("_paq.push(['trackPageView'])")
    expect(html).toContain('matomo.php?idsite=42')
  })

  it('leaves Matomo out when the visitor refused audience measurement', async () => {
    const html = await render(true, `1.0.${now}`)

    expect(html).not.toContain('_paq')
    expect(html).not.toContain('matomo.php')
  })

  it('tells the browser where Matomo lives, without contacting it, until a yes', async () => {
    const html = await render(true)

    expect(html).toContain(
      '<template id="matomo-config" data-url="https://stats.test" data-id="42"></template>'
    )
  })
})

describe('language cookie', () => {
  const now = Math.floor(Date.now() / 1000)

  beforeEach(() => vi.useFakeTimers({ toFake: ['Date'] }))
  afterEach(() => vi.useRealTimers())

  async function languageCookie(switchOn: boolean, consent?: string, current?: string) {
    const set = vi.fn()
    const jar: Record<string, string | undefined> = {
      comparia_cookie_consent: consent,
      PARAGLIDE_LOCALE: current
    }
    const event = {
      request: new Request('http://arene.test/'),
      locals: await localsFor(switchOn, jar),
      cookies: { get: (name: string) => jar[name], set }
    }
    await paraglideHandle({ event, resolve } as never)
    return set
  }

  it.each([
    ['the banner is off', false, undefined],
    ['nobody has answered', true, undefined],
    ['the visitor refused measurement', true, `1.0.${now}`]
  ])('lasts as long as today when %s', async (_case, switchOn, consent) => {
    const set = await languageCookie(switchOn, consent)

    expect(set).toHaveBeenCalledWith('PARAGLIDE_LOCALE', 'fr', {
      path: '/',
      httpOnly: false,
      maxAge: 1000
    })
  })

  it('leaves a cookie that already holds the locale alone', async () => {
    const set = await languageCookie(true, undefined, 'fr')

    expect(set).not.toHaveBeenCalled()
  })
})

describe('measurement in use', () => {
  const template = readFileSync(new URL('./app.html', import.meta.url), 'utf8').replaceAll(
    '%sveltekit.nonce%',
    'n0nce'
  )
  // A trimmed version of what svelte.config.js has SvelteKit send.
  const builtPolicy = "script-src 'self' 'nonce-n0nce'; connect-src 'self'; img-src 'self' data:"
  const now = Math.floor(Date.now() / 1000)

  beforeEach(() => vi.useFakeTimers({ toFake: ['Date'] }))
  afterEach(() => {
    vi.useRealTimers()
    privateEnv.MATOMO_URL = 'https://stats.test'
    privateEnv.MATOMO_ID = '42'
  })

  // Runs the handles that touch measurement in the order the hook sequence does.
  async function serve(switchOn: boolean, consent?: string) {
    clock += 60_000
    vi.setSystemTime(clock)
    request.mockResolvedValue({ cookie_banner_enabled: switchOn })
    const event = {
      locals: {} as App.Locals,
      cookies: { get: (name: string) => (name === 'comparia_cookie_consent' ? consent : undefined) }
    }
    const page = async (
      _event: unknown,
      opts?: { transformPageChunk?: (input: { html: string; done: boolean }) => string }
    ) =>
      new Response(opts?.transformPageChunk?.({ html: template, done: true }) ?? template, {
        headers: { 'content-security-policy': builtPolicy }
      })
    const response = await securityHeadersHandle({
      event,
      resolve: () =>
        cookieBannerHandle({
          event,
          resolve: () => matomoHandle({ event, resolve: page } as never)
        } as never)
    } as never)
    return {
      locals: event.locals,
      html: await response.text(),
      policy: response.headers.get('content-security-policy') ?? ''
    }
  }

  describe('with Matomo set on the server', () => {
    it.each([
      ['the banner is off', false, undefined],
      ['the visitor said yes', true, `1.1.${now}`]
    ])('loads Matomo and trusts its origin when %s', async (_case, switchOn, consent) => {
      const { locals, html, policy } = await serve(switchOn, consent)

      expect(locals.measurement).toEqual({ url: 'https://stats.test', id: '42' })
      expect(html).toContain("_paq.push(['setSiteId', '42'])")
      expect(policy).toBe(
        "script-src 'self' 'nonce-n0nce' https://stats.test; connect-src 'self' https://stats.test; img-src 'self' data: https://stats.test"
      )
    })

    it('asks first, and still trusts the origin so a yes can start Matomo', async () => {
      const { locals, html, policy } = await serve(true)

      expect(locals.cookieConsent.showBanner).toBe(true)
      expect(html).toContain('<template id="matomo-config"')
      expect(policy).toContain("script-src 'self' 'nonce-n0nce' https://stats.test")
    })
  })

  it('follows a change of address without a restart', async () => {
    privateEnv.MATOMO_URL = 'https://other-stats.test'

    const { html, policy } = await serve(false)

    expect(html).toContain("var u = 'https://other-stats.test/'")
    expect(policy).toContain('https://other-stats.test')
    expect(policy).not.toContain('https://stats.test')
  })
})
