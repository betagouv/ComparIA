import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// The Instance is mounted under /fr. Paraglide's own cookie strategy writes
// path=/, which every Instance of the origin would read, so the locale cookie
// goes through a strategy of ours that writes it on the Instance path.
const state = vi.hoisted(() => ({
  prefix: '/fr',
  client: undefined as
    undefined | { getLocale: () => string | undefined; setLocale: (l: string) => void },
  server: undefined as undefined | { getLocale: (request?: Request) => string | undefined }
}))

vi.mock('$app/paths', () => ({ resolve: (path: string) => `${state.prefix}${path}` }))
vi.mock('$lib/i18n/runtime', () => ({
  cookieName: 'PARAGLIDE_LOCALE',
  cookieMaxAge: 100,
  isLocale: (value: string) => ['fr', 'da', 'en'].includes(value),
  defineCustomClientStrategy: (_name: string, handler: never) => (state.client = handler),
  defineCustomServerStrategy: (_name: string, handler: never) => (state.server = handler)
}))

await import('./localeCookie')

describe('locale cookie strategy', () => {
  let written: string[]

  beforeEach(() => {
    written = []
    state.prefix = '/fr'
    vi.spyOn(document, 'cookie', 'set').mockImplementation((value) => {
      written.push(value)
    })
    vi.stubGlobal('location', { protocol: 'https:' })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('writes the chosen locale on the Instance path, and nowhere else', () => {
    state.client!.setLocale('da')

    expect(written).toHaveLength(1)
    expect(written[0]).toMatch(
      /^PARAGLIDE_LOCALE=da; path=\/fr; max-age=100; samesite=lax; secure$/
    )
  })

  it('writes on the root path, as before, with no Instance path', () => {
    state.prefix = ''

    state.client!.setLocale('da')

    expect(written[0]).toMatch(/^PARAGLIDE_LOCALE=da; path=\/;/)
  })

  it('reads the locale from the cookies of the page', () => {
    vi.spyOn(document, 'cookie', 'get').mockReturnValue('theme=dark; PARAGLIDE_LOCALE=en')

    expect(state.client!.getLocale()).toBe('en')
  })

  it('reads the locale from the cookie header of a request, and ignores an unknown one', () => {
    const request = (cookie: string) =>
      new Request('http://arene.test/fr/', { headers: { cookie } })

    expect(state.server!.getLocale(request('a=1; PARAGLIDE_LOCALE=da'))).toBe('da')
    expect(state.server!.getLocale(request('PARAGLIDE_LOCALE=xx'))).toBeUndefined()
    expect(state.server!.getLocale(request('a=1'))).toBeUndefined()
  })
})
