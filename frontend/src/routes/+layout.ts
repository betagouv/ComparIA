import type { VotesData } from '$lib/global.svelte'
import type { APIBotModel, APIData } from '$lib/models'
import mockModels from '$lib/mockModels.json'

// TEMP MOCKUP STUB — serves the local catalog (frontend/src/lib/mockModels.json)
// so the redesigned model card can be tested with `vite dev` without the backend.
// Restore the original API-backed load from /tmp/layout.ts.bak when done.
export async function load() {
  const data: APIData = {
    data_timestamp: Date.now() / 1000,
    models: mockModels as unknown as APIBotModel[]
  }
  const votes: VotesData = { count: 123456, objective: 1000000 }
  return { data, votes }
}
