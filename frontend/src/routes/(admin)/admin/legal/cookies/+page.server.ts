import { serverMatomo } from '$lib/server/matomo'
import type { PageServerLoad } from './$types'

// What Server setting means: the Matomo this frontend server was given. Every
// page already carries these two values in its HTML, so nothing new leaks.
export const load: PageServerLoad = () => ({ serverMatomo: serverMatomo() })
