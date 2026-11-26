import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// The Instance is mounted under a path, '/fr' here or nothing: the Gateway
// removes it before the backend, so the browser has to put it in front of /api.
const state = vi.hoisted(() => ({
  prefix: '/fr',
  browser: true,
  publicEnv: {} as Record<string, string>
}))

vi.mock('$app/environment', () => ({
  get browser() {
    return state.browser
  },
  dev: false
}))
vi.mock('$app/paths', () => ({ resolve: (path: string) => `${state.prefix}${path}` }))
vi.mock('$env/dynamic/public', () => ({ env: state.publicEnv }))

const { api } = await import('./fastapi-client')

describe('API base of the browser', () => {
  beforeEach(() => {
    state.browser = true
    state.prefix = '/fr'
    for (const key of Object.keys(state.publicEnv)) delete state.publicEnv[key]
    vi.stubGlobal('window', { location: { origin: 'https://arene.test' } })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('is origin + Instance path + /api when the API is served from the app origin', () => {
    expect(api.getUrl('/counter')).toBe('https://arene.test/fr/api/counter')
  })

  it('is origin + /api with no Instance path', () => {
    state.prefix = ''

    expect(api.getUrl('/counter')).toBe('https://arene.test/api/counter')
  })

  it('leaves an explicitly configured separate API origin untouched', () => {
    state.publicEnv.PUBLIC_API_DEV_MODE = 'true'
    state.publicEnv.PUBLIC_API_URL = 'http://localhost:8008'

    expect(api.getUrl('/counter')).toBe('http://localhost:8008/api/counter')
    expect(api.getPublicUrl('/counter')).toBe('http://localhost:8008/api/counter')
  })

  it('puts the Instance path in the URLs the browser loads itself', () => {
    expect(api.getPublicUrl('/auth/config/logo', { v: '3' })).toBe('/fr/api/auth/config/logo?v=3')
  })

  it('keeps the in-cluster address, with no Instance path, for server-side calls', () => {
    state.browser = false
    state.publicEnv.PUBLIC_API_LOCAL_URL = 'http://backend:8001'

    expect(api.getUrl('/counter')).toBe('http://backend:8001/api/counter')
  })
})
