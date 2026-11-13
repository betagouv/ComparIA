import { resolve } from '$app/paths'
import { redirect } from '@sveltejs/kit'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async () => {
  redirect(302, resolve('/admin/activite'))
}
