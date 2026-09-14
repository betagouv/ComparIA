import { env } from '$env/dynamic/private'
import { baseLocale } from '$lib/i18n/runtime'
import type { PageServerLoad } from './$types'

// The label written in this language is the one that mints the published key,
// so the form flags it and sends it first. DEFAULT_LOCALE is what a visitor
// with no cookie gets, see hooks.server.ts.

export const load: PageServerLoad = async () => {
  return { defaultLocale: env.DEFAULT_LOCALE || baseLocale }
}
