import type { AdminSuggestion, AdminSuggestionCategory } from '$lib/generated/admin'
import type { Locale } from '$lib/i18n/runtime'

export type SuggestionStatus = AdminSuggestion['status']

export type SuggestionCategory = Required<AdminSuggestionCategory>
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
  locale: Locale
  category_id: string
}
