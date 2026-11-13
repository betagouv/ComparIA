import { api } from '$lib/fastapi-client'
import type { SelectionModeTemplate } from '$lib/generated/admin'
import { loadCohorts } from '../cohorts'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ fetch }) => {
  const [templates, cohorts] = await Promise.all([
    api.request<SelectionModeTemplate[]>('/admin/selection-modes/templates', { fetch }),
    loadCohorts(fetch)
  ])
  return { templates, cohorts }
}
