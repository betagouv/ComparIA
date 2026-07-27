import type { AdminSuggestion, AdminSuggestionCategory } from '$lib/generated/admin'

export type SuggestionStatus = AdminSuggestion['status']

export type SuggestionCategory = AdminSuggestionCategory
export type PromptSuggestion = AdminSuggestion

export interface SuggestionsPage {
  items: PromptSuggestion[]
  total: number
  page: number
  page_size: number
  categories: SuggestionCategory[]
}

export interface SuggestionFilters {
  search: string
  status: '' | SuggestionStatus
  locale: string
  category_id: string
}
