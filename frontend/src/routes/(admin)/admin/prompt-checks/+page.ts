import { api } from '$lib/fastapi-client'
import type { PromptCheckStatus } from '$lib/generated/admin'
import type { PageLoad } from './$types'
import type { PromptCheckStats } from './types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:prompt-check')

  const [check, stats] = await Promise.all([
    api.request<PromptCheckStatus>('/admin/prompt-check', { fetch }),
    // Les compteurs ne doivent pas emporter la page de configuration avec eux.
    api
      .request<PromptCheckStats>('/admin/prompt-check/stats?period=all', { fetch })
      .catch(() => null)
  ])

  return { check, stats }
}
