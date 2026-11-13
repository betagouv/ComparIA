import { error } from '@sveltejs/kit'
import { loadCohorts } from '../cohorts'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ parent, params, fetch }) => {
  const [{ modes }, cohorts] = await Promise.all([parent(), loadCohorts(fetch)])
  const mode = modes.find((item) => item.id === params.id)
  if (!mode) error(404)
  return { mode, cohorts }
}
