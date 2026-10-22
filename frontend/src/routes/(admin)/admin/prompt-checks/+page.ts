import { api } from '$lib/fastapi-client'
import type { PromptCheckStatus } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import type { PageLoad } from './$types'
import type { PromptCheckModel, PromptCheckStats } from './types'

export const load: PageLoad = async ({ depends, fetch }) => {
  depends('admin:prompt-check')

  const [check, schema, stats, models] = await Promise.all([
    api.request<PromptCheckStatus>('/admin/prompt-check', { fetch }),
    api.request<JSONSchema>('/admin/prompt-check/schema', { fetch }),
    // Les compteurs ne doivent pas emporter la page de configuration avec eux.
    api
      .request<PromptCheckStats>('/admin/prompt-check/stats', {
        searchParams: { period: 'all' },
        fetch
      })
      .catch(() => null),
    // The list only helps typing: the field takes any id.
    api
      .request<PromptCheckModel[]>('/admin/prompt-check/models', { fetch })
      .catch(() => [] as PromptCheckModel[])
  ])

  return { check, schema, stats, models }
}
