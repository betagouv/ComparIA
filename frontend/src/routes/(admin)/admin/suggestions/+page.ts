import { api } from '$lib/fastapi-client'
import type { PageLoad } from './$types'
import type { SuggestionFilters, SuggestionsPage } from './types'

export const load: PageLoad = async ({ depends, fetch, url }) => {
  const filters: SuggestionFilters = {
    search: url.searchParams.get('search') ?? '',
    status: (url.searchParams.get('status') as SuggestionFilters['status']) ?? '',
    locale: url.searchParams.get('language') ?? '',
    category_id: url.searchParams.get('category_id') ?? ''
  }
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value)
  }

  const suggestions = await api.request<SuggestionsPage>(`/admin/suggestions?${params}`, { fetch })

  depends('admin:suggestions')

  return { filters, suggestions }
}
