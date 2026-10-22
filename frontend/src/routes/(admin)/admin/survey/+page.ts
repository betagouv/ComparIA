import { api } from '$lib/fastapi-client'
import type { AdminSurveyResponse } from '$lib/generated/admin'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:survey')

  return {
    survey: await api.request<AdminSurveyResponse>('/admin/survey', { fetch })
  }
}
