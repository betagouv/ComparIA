import { loadInformationalPages } from '$lib/informational-pages.server'
import type { LayoutServerLoad } from './$types'

export const load: LayoutServerLoad = async ({ fetch }) => ({
  informationalPages: await loadInformationalPages(fetch)
})
