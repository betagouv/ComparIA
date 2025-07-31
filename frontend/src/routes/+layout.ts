import { getVotes } from '$lib/global.svelte'

export async function load() {
  getVotes()
}
