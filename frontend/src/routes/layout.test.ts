import { beforeEach, describe, expect, it, vi } from 'vitest'
import { load } from './+layout'

const request = vi.fn()

vi.mock('$lib/fastapi-client', () => ({
  api: { request: (...args: unknown[]) => request(...args) }
}))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => 'fr' }))

const bannerText = { title: 'Cookies' }
const stats = { url: 'https://stats.test', id: '42' }

async function runLoad(
  serverSwitch: boolean,
  configSwitch: boolean,
  measurement: { url: string; id: string } | null = stats
) {
  request.mockImplementation(async (path: string) => {
    if (path === '/auth/config') return { cookie_banner_enabled: configSwitch }
    if (path === '/settings/legal/cookies') return bannerText
    return {}
  })
  return (await load({
    data: { cookieBannerEnabled: serverSwitch, measurement },
    depends: vi.fn(),
    fetch: vi.fn()
  } as unknown as Parameters<typeof load>[0])) as Record<string, unknown>
}

describe('root layout load', () => {
  beforeEach(() => request.mockReset())

  it('asks for the banner text when the server rendered with the switch on', async () => {
    const data = await runLoad(true, false)

    expect(data.cookieBannerEnabled).toBe(true)
    expect(data.cookieBanner).toEqual(bannerText)
  })

  it('leaves the banner out when the server rendered with the switch off', async () => {
    const data = await runLoad(false, true)

    expect(data.cookieBannerEnabled).toBe(false)
    expect(data.cookieBanner).toBeNull()
    expect(request).not.toHaveBeenCalledWith('/settings/legal/cookies', expect.anything())
  })

  it('passes on the measurement the server rendered with', async () => {
    expect((await runLoad(true, true)).measurement).toEqual(stats)
    expect((await runLoad(true, true, null)).measurement).toBeNull()
  })

  it('leaves the banner out when nothing is measured, even with the switch on', async () => {
    const data = await runLoad(true, true, null)

    expect(data.cookieBanner).toBeNull()
    expect(request).not.toHaveBeenCalledWith('/settings/legal/cookies', expect.anything())
  })
})
