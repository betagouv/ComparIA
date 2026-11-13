import { beforeEach, describe, expect, it, vi } from 'vitest'

const { env, publicEnv } = vi.hoisted(() => ({
  env: {} as Record<string, string>,
  publicEnv: {} as Record<string, string>
}))

vi.mock('$env/dynamic/private', () => ({ env }))
vi.mock('$env/dynamic/public', () => ({ env: publicEnv }))
vi.mock('$lib/metrics', () => ({ getMetrics: async () => 'http_requests_total 1' }))

const { GET } = await import('./+server')

async function scrape(authorization?: string) {
  const headers = authorization ? { authorization } : undefined
  const request = new Request('http://arene.test/metrics', { headers })
  return GET({ request } as never)
}

describe('frontend /metrics', () => {
  beforeEach(() => {
    for (const key of Object.keys(env)) delete env[key]
    for (const key of Object.keys(publicEnv)) delete publicEnv[key]
  })

  it('refuses everyone when no token is set', async () => {
    expect((await scrape()).status).toBe(401)
    expect((await scrape('Bearer anything')).status).toBe(401)
  })

  it('stays open in debug when no token is set', async () => {
    publicEnv.PUBLIC_LANGUIA_DEBUG = 'true'
    expect((await scrape()).status).toBe(200)
  })

  it('answers only the right bearer token', async () => {
    env.METRICS_TOKEN = 's3cret'
    expect((await scrape()).status).toBe(401)
    expect((await scrape('Bearer wrong')).status).toBe(401)
    expect((await scrape('Basic s3cret')).status).toBe(401)
    const response = await scrape('bearer s3cret')
    expect(response.status).toBe(200)
    expect(await response.text()).toBe('http_requests_total 1')
  })
})
