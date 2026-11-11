import { resolve } from '$app/paths'
import { redirect } from '@sveltejs/kit'
import type { PageLoad } from './$types'

export const load: PageLoad = ({ url }) => {
  redirect(307, resolve(`/admin/activite/apercu${url.search}`))
}
