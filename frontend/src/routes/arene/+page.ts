import { getModels } from '$lib/models'
import { getVotes } from '$lib/state.svelte'

export async function load() {
  getVotes()
  const models = await getModels()
  
  return { models }
}
