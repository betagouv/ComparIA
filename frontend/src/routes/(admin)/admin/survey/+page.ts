import { api } from '$lib/fastapi-client'
import type { AdminSurveyResponse } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch, data }) => {
  depends('admin:survey')

  return {
    ...data,
    survey: await api.request<AdminSurveyResponse>('/admin/survey', { fetch })
  }
}
