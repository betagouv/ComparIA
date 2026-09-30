import { collectDefaultMetrics, Counter, Histogram, register } from 'prom-client'

// Collect default metrics (CPU, memory, etc.)
collectDefaultMetrics()

// HTTP request counter
export const httpRequestCounter = new Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status']
})

// HTTP request duration histogram
export const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10]
})

// Export metrics
export async function getMetrics(): Promise<string> {
  return register.metrics()
}
