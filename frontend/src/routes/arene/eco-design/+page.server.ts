import { loadInformationalPage } from '$lib/informational-page-route.server'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = ({ fetch }) => loadInformationalPage('ecodesign', fetch)
