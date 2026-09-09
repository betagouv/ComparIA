import { beforeEach, describe, expect, it, vi } from 'vitest'

const { request, privateEnv } = vi.hoisted(() => ({
  request: vi.fn(),
  privateEnv: { AUTH_ACCESS_POLICY: 'sign_in_required' } as Record<string, string>
}))

vi.mock('$env/dynamic/private', () => ({ env: privateEnv }))
vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/fastapi-client', () => ({ api: { request }, UnauthorizedError: class {} }))
vi.mock('$lib/i18n/runtime', () => ({ defineCustomServerStrategy: () => {} }))
vi.mock('$lib/i18n/server', () => ({ paraglideMiddleware: () => {} }))
vi.mock('$lib/logger.server', () => ({ logger: { error: () => {}, info: () => {} } }))
vi.mock('$lib/metrics', () => ({
  httpRequestCounter: { inc: () => {} },
  httpRequestDuration: { observe: () => {} }
}))

const { authWallHandle, handleFetch } = await import('./hooks.server')

const resolve = vi.fn(async () => new Response('page'))

function eventWith(cookie?: string) {
  const deleted: string[] = []
  return {
    deleted,
    event: {
      url: new URL('http://arene.test/statistics'),
      cookies: {
        get: () => cookie,
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
