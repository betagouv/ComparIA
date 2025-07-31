import { getModels } from '$lib/models'

export async function load() {
  const models = await getModels()
  
  return { models }
}
