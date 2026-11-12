import { api } from '$lib/fastapi-client'
import type { ActivityFilterOptions } from '$lib/generated/admin'

/**
 * Cohorts seen in comparisons, offered while typing in the editor. Only
 * suggestions: the editor works without them.
 */
export function loadCohorts(fetch: typeof globalThis.fetch): Promise<string[]> {
  return api
    .request<ActivityFilterOptions>('/admin/activity/filters', { fetch })
    .then((options) => options.cohorts)
    .catch(() => [])
}
