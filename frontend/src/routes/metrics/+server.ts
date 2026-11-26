import { env } from '$env/dynamic/private'
import { env as publicEnv } from '$env/dynamic/public'
import { getMetrics } from '$lib/metrics'
import { createHash, timingSafeEqual } from 'node:crypto'
import type { RequestHandler } from './$types'

const digest = (value: string) => createHash('sha256').update(value).digest()

// Same rule as the backend's /metrics: without a token the endpoint answers
// nobody outside debug, so a deployment that forgot one gets a failing scrape,
// not public metrics. Every path outside /api reaches this server.
function authorized(header: string | null): boolean {
  const token = env.METRICS_TOKEN
  if (!token) return publicEnv.PUBLIC_LANGUIA_DEBUG === 'true'
  // The scheme is case-insensitive (RFC 6750), the credential is not.
  const given = /^bearer (.*)$/i.exec(header ?? '')?.[1]
  return given !== undefined && timingSafeEqual(digest(given), digest(token))
}

export const GET: RequestHandler = async ({ request }) => {
  if (!authorized(request.headers.get('authorization'))) {
    return new Response('Unauthorized', { status: 401 })
  }

  const metrics = await getMetrics()

  return new Response(metrics, {
    headers: {
      'Content-Type': 'text/plain; version=0.0.4'
    }
  })
}
