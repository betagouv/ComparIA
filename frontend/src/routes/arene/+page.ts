import { getVotes } from '$lib/global.svelte'
import { getModels } from '$lib/models'

export async function load() {
  getVotes()
  const models = await getModels()
  
  return { models }
}
