import { getMetrics } from '$lib/metrics'
import type { RequestHandler } from './$types'

export const GET: RequestHandler = async () => {
  const metrics = await getMetrics()

  return new Response(metrics, {
    headers: {
      'Content-Type': 'text/plain; version=0.0.4'
    }
  })
}
