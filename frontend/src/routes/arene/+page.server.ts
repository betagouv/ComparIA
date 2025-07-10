// import { api } from "$lib/api";
// import type { Model } from "$lib/chatService.svelte";

export async function load() {
    // const result = await api.predict('/enter_arena')
	// return { models: (result.data as [Model[]])[0] }
    return { models: [] }
}