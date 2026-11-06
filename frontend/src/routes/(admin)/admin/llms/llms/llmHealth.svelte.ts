import { api } from '$lib/fastapi-client'
import type { LLMHealth } from '$lib/generated/admin'
import { SvelteMap } from 'svelte/reactivity'
import type { LLMHealthResult } from './types'

const MAX_PARALLEL_TESTS = 5

export function useLLMHealth() {
  const results = new SvelteMap<string, LLMHealthResult>()
  let running = $state(false)
  let total = $state(0)

  async function testOne(id: string) {
    try {
      results.set(
        id,
        await api.request<LLMHealth>(`/admin/llms/llm/${id}/health`, { method: 'POST' })
      )
    } catch {
      results.set(id, { healthy: false, latency_ms: null, error: 'request_failed' })
    }
  }

  async function testAll(ids: string[]) {
    results.clear()
    total = ids.length
    running = true
    const queue = [...ids]
    await Promise.all(
      Array.from({ length: MAX_PARALLEL_TESTS }, async () => {
        while (queue.length) await testOne(queue.shift()!)
      })
    )
    running = false
  }

  return {
    results,
    testAll,
    get running() {
      return running
    },
    get total() {
      return total
    }
  }
}
